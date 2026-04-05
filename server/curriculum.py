"""
Adaptive Curriculum Manager
----------------------------
Dynamically adjusts task difficulty based on agent performance history.
Implements promotion/demotion thresholds with a sliding window.

Levels:
  0 - easy_only: Only easy tasks (onboarding)
  1 - easy_medium: Easy + medium, weighted toward medium
  2 - medium_hard: Medium + hard, weighted toward hard
  3 - expert: Hard tasks + multi-bug injection (2+ bugs per query)
"""

from __future__ import annotations

import random
import threading
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class CurriculumState:
    """Tracks agent performance for curriculum decisions.

    Attributes:
        total_episodes: Cumulative count of all episodes recorded since
            instantiation, regardless of level transitions.
        current_level: Integer index into ``CurriculumManager.LEVELS``
            representing the active difficulty tier (0–3).
        level_episodes: Number of episodes completed since the last level
            transition.  Resets to 0 on every promotion or demotion.
        recent_rewards: Rolling window of the most recent 30 episode
            rewards used for aggregate promotion/demotion decisions.
        rewards_by_difficulty: Per-difficulty rolling windows (maxlen 20)
            that allow fine-grained inspection of per-category performance.
    """

    total_episodes: int = 0
    current_level: int = 0
    level_episodes: int = 0
    recent_rewards: deque = field(default_factory=lambda: deque(maxlen=30))
    rewards_by_difficulty: Dict[str, deque] = field(
        default_factory=lambda: {
            "easy": deque(maxlen=20),
            "medium": deque(maxlen=20),
            "hard": deque(maxlen=20),
        }
    )


class CurriculumManager:
    """Adaptive difficulty selection based on rolling performance.

    The manager maintains a :class:`CurriculumState` and applies
    promotion/demotion rules after every recorded episode.  Difficulty
    sampling is weighted according to the active curriculum level so the
    agent is always exposed to tasks that are *slightly* beyond its
    current comfort zone while still seeing easier examples for
    consolidation.

    Level progression
    -----------------
    - **0 – easy_only**: 100 % easy tasks.  Used during initial onboarding
      so the agent can establish baseline SQL repair skills.
    - **1 – easy_medium**: 30 % easy / 70 % medium.  Introduces medium
      difficulty while providing easy anchors.
    - **2 – medium_hard**: 30 % medium / 70 % hard.  Pushes toward hard
      queries while retaining medium exposure.
    - **3 – expert**: 100 % hard tasks.  Additionally, :attr:`is_expert_mode`
      becomes ``True``, signalling the environment to inject 2 or more bugs
      per query for maximum challenge.

    Promotion / demotion
    --------------------
    Promotion occurs when the rolling average over the last
    ``min_episodes_for_promotion`` rewards exceeds
    ``promotion_threshold``.  Demotion occurs when the rolling average
    over the last ``min_episodes_for_demotion`` rewards falls at or below
    ``demotion_threshold``.  Both transitions reset ``level_episodes`` to
    ensure a minimum observation period at the new level before the next
    possible transition.

    Parameters
    ----------
    promotion_threshold:
        Minimum mean reward (over the promotion window) required to
        advance one level.  Default ``0.85``.
    demotion_threshold:
        Maximum mean reward (over the demotion window) that triggers a
        step back.  Default ``0.4``.
    min_episodes_for_promotion:
        Minimum number of episodes that must be completed at the current
        level before a promotion can be triggered.  Default ``10``.
    min_episodes_for_demotion:
        Minimum number of episodes that must be completed at the current
        level before a demotion can be triggered.  Default ``5``.

    Examples
    --------
    >>> mgr = CurriculumManager()
    >>> difficulty = mgr.select_difficulty()
    >>> mgr.record_episode(difficulty, reward=1.0)
    >>> mgr.get_info()["level_name"]
    'easy_only'
    """

    LEVELS: List[str] = ["easy_only", "easy_medium", "medium_hard", "expert"]

    # Difficulty weights per level: {difficulty: weight}
    LEVEL_WEIGHTS: Dict[int, Dict[str, float]] = {
        0: {"easy": 1.0},
        1: {"easy": 0.3, "medium": 0.7},
        2: {"medium": 0.3, "hard": 0.7},
        3: {"hard": 1.0},  # Expert uses hard tasks but with multi-bug injection
    }

    def __init__(
        self,
        promotion_threshold: float = 0.85,
        demotion_threshold: float = 0.4,
        min_episodes_for_promotion: int = 10,
        min_episodes_for_demotion: int = 5,
    ) -> None:
        """Initialise the curriculum manager with configurable thresholds.

        Parameters
        ----------
        promotion_threshold:
            Mean reward required over the promotion window to advance.
        demotion_threshold:
            Mean reward at or below which the agent is demoted.
        min_episodes_for_promotion:
            Minimum level-local episodes before promotion is evaluated.
        min_episodes_for_demotion:
            Minimum level-local episodes before demotion is evaluated.
        """
        self._lock = threading.Lock()
        self._state: CurriculumState = CurriculumState()
        self._promotion_threshold: float = promotion_threshold
        self._demotion_threshold: float = demotion_threshold
        self._min_promo: int = min_episodes_for_promotion
        self._min_demo: int = min_episodes_for_demotion

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def select_difficulty(self, rng: Optional[random.Random] = None) -> str:
        """Sample a task difficulty according to the current curriculum level.

        The sampling is weighted so that higher levels favour harder
        difficulties, matching the ``LEVEL_WEIGHTS`` configuration.

        Parameters
        ----------
        rng:
            Optional :class:`random.Random` instance for reproducible
            sampling (e.g. during unit tests or seeded rollouts).  When
            ``None`` a fresh unseeded instance is used.

        Returns
        -------
        str
            One of ``"easy"``, ``"medium"``, or ``"hard"``.
        """
        r: random.Random = rng or random.Random()
        with self._lock:
            weights: Dict[str, float] = self.LEVEL_WEIGHTS[self._state.current_level]
        difficulties: List[str] = list(weights.keys())
        probs: List[float] = list(weights.values())
        return r.choices(difficulties, weights=probs, k=1)[0]

    @property
    def is_expert_mode(self) -> bool:
        """``True`` when the current level enables multi-bug injection.

        At expert level (3) the environment should inject 2 or more bugs
        into each query to maximise task complexity.  Callers should check
        this flag before constructing episode tasks.

        Returns
        -------
        bool
        """
        with self._lock:
            return self._state.current_level >= 3

    def record_episode(self, difficulty: str, reward: float) -> None:
        """Record the outcome of a completed episode.

        Updates total and level-local episode counters, appends the reward
        to the appropriate rolling windows, and evaluates whether a level
        transition should occur.

        Parameters
        ----------
        difficulty:
            The difficulty label of the completed episode.  Must be one of
            ``"easy"``, ``"medium"``, or ``"hard"``; unrecognised values
            are silently ignored for the per-difficulty window but still
            count toward aggregate statistics.
        reward:
            Scalar reward signal for the episode.  Expected to be in
            ``[0.0, 1.0]`` but not enforced; the manager operates on raw
            values.
        """
        with self._lock:
            self._state.total_episodes += 1
            self._state.level_episodes += 1
            self._state.recent_rewards.append(reward)
            if difficulty in self._state.rewards_by_difficulty:
                self._state.rewards_by_difficulty[difficulty].append(reward)
            self._maybe_adjust_level()

    def get_info(self) -> Dict[str, Any]:
        """Return a snapshot of the current curriculum state.

        Intended for logging, TensorBoard scalars, and environment ``info``
        dictionaries so training dashboards can track curriculum progress
        without coupling to internal state.

        Returns
        -------
        Dict[str, Any]
            Keys:

            - ``current_level`` (int): Active level index (0–3).
            - ``level_name`` (str): Human-readable level label.
            - ``is_expert_mode`` (bool): Whether multi-bug injection is active.
            - ``total_episodes`` (int): Lifetime episode count.
            - ``level_episodes`` (int): Episodes since last transition.
            - ``rolling_avg_reward`` (float): Mean over ``recent_rewards``;
              ``0.0`` when no episodes have been recorded.
            - ``promotion_threshold`` (float): Configured promotion cutoff.
            - ``demotion_threshold`` (float): Configured demotion cutoff.
        """
        with self._lock:
            recent: List[float] = list(self._state.recent_rewards)
            return {
                "current_level": self._state.current_level,
                "level_name": self.LEVELS[self._state.current_level],
                "is_expert_mode": self._state.current_level >= 3,
                "total_episodes": self._state.total_episodes,
                "level_episodes": self._state.level_episodes,
                "rolling_avg_reward": sum(recent) / len(recent) if recent else 0.0,
                "promotion_threshold": self._promotion_threshold,
                "demotion_threshold": self._demotion_threshold,
            }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _maybe_adjust_level(self) -> None:
        """Evaluate and apply promotion or demotion if conditions are met.

        Called automatically by :meth:`record_episode` after every update.
        Only one transition (promotion *or* demotion) can occur per call;
        promotion is checked first.  After a transition ``level_episodes``
        is reset to ``0`` to enforce the minimum observation period at the
        new level.
        """
        level: int = self._state.current_level
        recent: List[float] = list(self._state.recent_rewards)

        # Promotion check — only possible below the maximum level
        if (
            level < 3
            and self._state.level_episodes >= self._min_promo
            and len(recent) >= self._min_promo
        ):
            window: List[float] = recent[-self._min_promo :]
            if sum(window) / len(window) >= self._promotion_threshold:
                self._state.current_level = min(3, level + 1)
                self._state.level_episodes = 0
                return  # Skip demotion check after a promotion

        # Demotion check — only possible above the minimum level
        if (
            level > 0
            and self._state.level_episodes >= self._min_demo
            and len(recent) >= self._min_demo
        ):
            window = recent[-self._min_demo :]
            if sum(window) / len(window) <= self._demotion_threshold:
                self._state.current_level = max(0, level - 1)
                self._state.level_episodes = 0
