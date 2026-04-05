"""
Episode analytics collector for the RL SQL debugging environment.

Tracks per-episode metrics and aggregates training statistics for observability.
No external dependencies — stdlib only.
"""

from __future__ import annotations

import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class EpisodeMetrics:
    """Detailed metrics for a single episode."""

    episode_id: str
    task_id: str
    difficulty: str
    total_steps: int
    final_reward: float
    reward_trajectory: List[float]          # Reward at each step
    correctness_trajectory: List[float]     # Correctness at each step
    regression_count: int                   # Times correctness dropped vs previous step
    bug_type: str                           # Type of injected bug
    was_bug_fixed: bool                     # Did agent achieve correctness == 1.0
    unique_queries_submitted: int           # Number of distinct queries tried
    reward_components: Dict[str, float]     # Final step's reward decomposition


# ---------------------------------------------------------------------------
# Internal state for an in-progress episode
# ---------------------------------------------------------------------------

@dataclass
class _InProgressEpisode:
    """Mutable accumulator for a single episode that has not yet been finalised."""

    episode_id: str
    task_id: str
    difficulty: str
    bug_type: str
    reward_trajectory: List[float] = field(default_factory=list)
    correctness_trajectory: List[float] = field(default_factory=list)
    queries_seen: set = field(default_factory=set)
    last_reward_components: Dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Collector
# ---------------------------------------------------------------------------

class AnalyticsCollector:
    """Collects and aggregates episode analytics for training observability.

    Thread-safe: all public methods acquire an internal lock so that
    concurrent sessions can safely share a single collector instance.
    """

    def __init__(self, max_history: int = 1000) -> None:
        """Initialise the collector.

        Args:
            max_history: Maximum number of completed episodes to retain in the
                rolling history buffer.  Older episodes are evicted automatically.
        """
        self._lock = threading.Lock()
        self._max_history = max_history
        # Keyed by episode_id; holds episodes that have been started but not
        # yet finalised via finish_episode().
        self._in_progress: Dict[str, _InProgressEpisode] = {}
        # Fixed-size ring-buffer of completed EpisodeMetrics objects.
        self._history: deque[EpisodeMetrics] = deque(maxlen=max_history)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start_episode(
        self,
        episode_id: str,
        task_id: str,
        difficulty: str,
        bug_type: str,
    ) -> None:
        """Begin tracking a new episode.

        Silently replaces any previously started episode with the same
        episode_id to handle environment resets without an explicit finish.

        Args:
            episode_id: Unique identifier for this episode.
            task_id:    Identifier of the SQL task being solved.
            difficulty: Difficulty label (e.g. "easy", "medium", "hard").
            bug_type:   Label describing the injected bug category.
        """
        with self._lock:
            self._in_progress[episode_id] = _InProgressEpisode(
                episode_id=episode_id,
                task_id=task_id,
                difficulty=difficulty,
                bug_type=bug_type,
            )

    def record_step(
        self,
        episode_id: str,
        reward: float,
        correctness: float,
        query: str,
        reward_components: Optional[Dict[str, float]] = None,
    ) -> None:
        """Record a single step within an episode.

        Silently ignores the call if episode_id is not currently being
        tracked (e.g. if start_episode was never called).

        Args:
            episode_id:        Episode this step belongs to.
            reward:            Scalar reward received at this step.
            correctness:       Fraction of expected output rows matched [0, 1].
            query:             The SQL query submitted at this step.
            reward_components: Optional breakdown of the reward scalar into
                               named sub-components (e.g. correctness_bonus,
                               syntax_penalty).  The most recent non-None
                               value is stored and returned in EpisodeMetrics.
        """
        with self._lock:
            ep = self._in_progress.get(episode_id)
            if ep is None:
                return

            ep.reward_trajectory.append(reward)
            ep.correctness_trajectory.append(correctness)
            ep.queries_seen.add(query)
            if reward_components is not None:
                ep.last_reward_components = dict(reward_components)

    def finish_episode(self, episode_id: str) -> EpisodeMetrics:
        """Finalise an episode and compute its aggregate metrics.

        Moves the episode from the in-progress dict to the completed history
        deque.  If the episode_id is not found (e.g. start_episode was never
        called) a minimal placeholder EpisodeMetrics with zero/empty values is
        returned and nothing is appended to the history.

        Args:
            episode_id: The episode to finalise.

        Returns:
            The completed EpisodeMetrics for the episode.
        """
        with self._lock:
            ep = self._in_progress.pop(episode_id, None)
            if ep is None:
                # Return a safe placeholder so callers never receive None.
                return EpisodeMetrics(
                    episode_id=episode_id,
                    task_id="",
                    difficulty="",
                    total_steps=0,
                    final_reward=0.0,
                    reward_trajectory=[],
                    correctness_trajectory=[],
                    regression_count=0,
                    bug_type="",
                    was_bug_fixed=False,
                    unique_queries_submitted=0,
                    reward_components={},
                )

            # Compute regression count: number of steps where correctness fell
            # compared to the immediately preceding step.
            regression_count = 0
            ct = ep.correctness_trajectory
            for i in range(1, len(ct)):
                if ct[i] < ct[i - 1]:
                    regression_count += 1

            metrics = EpisodeMetrics(
                episode_id=ep.episode_id,
                task_id=ep.task_id,
                difficulty=ep.difficulty,
                total_steps=len(ep.reward_trajectory),
                final_reward=ep.reward_trajectory[-1] if ep.reward_trajectory else 0.0,
                reward_trajectory=list(ep.reward_trajectory),
                correctness_trajectory=ct,
                regression_count=regression_count,
                bug_type=ep.bug_type,
                was_bug_fixed=bool(ct and ct[-1] >= 1.0),
                unique_queries_submitted=len(ep.queries_seen),
                reward_components=dict(ep.last_reward_components),
            )
            self._history.append(metrics)
            return metrics

    def get_summary(self) -> Dict[str, Any]:
        """Return aggregate statistics across all completed episodes.

        Returns an empty-safe dict when no episodes have been completed yet.

        Returns:
            A dict with the following keys:

            - ``total_episodes`` (int): Number of completed episodes retained
              in history.
            - ``avg_reward`` (float): Mean final reward across all episodes.
            - ``avg_reward_by_difficulty`` (Dict[str, float]): Mean final
              reward broken down by difficulty label.
            - ``avg_steps_to_solve`` (float): Mean total_steps for episodes
              where ``was_bug_fixed`` is True.  ``None`` if no successes.
            - ``success_rate`` (float): Fraction of episodes where the bug
              was fully fixed [0.0, 1.0].
            - ``success_rate_by_difficulty`` (Dict[str, float]): Success rate
              per difficulty label.
            - ``success_rate_by_bug_type`` (Dict[str, float]): Success rate
              per bug_type label.
            - ``avg_regression_count`` (float): Mean regression count per
              episode.
            - ``recent_trend`` (float): Difference between the mean reward of
              the most recent 20 episodes and the 20 episodes before that.
              ``None`` when fewer than 40 episodes are available.
        """
        with self._lock:
            history = list(self._history)
        total = len(history)

        if total == 0:
            return {
                "total_episodes": 0,
                "avg_reward": 0.0,
                "avg_reward_by_difficulty": {},
                "avg_steps_to_solve": None,
                "success_rate": 0.0,
                "success_rate_by_difficulty": {},
                "success_rate_by_bug_type": {},
                "avg_regression_count": 0.0,
                "recent_trend": None,
            }

        # ---------- overall avg reward ----------
        avg_reward = sum(m.final_reward for m in history) / total

        # ---------- avg reward by difficulty ----------
        reward_by_diff: Dict[str, List[float]] = defaultdict(list)
        for m in history:
            reward_by_diff[m.difficulty].append(m.final_reward)
        avg_reward_by_difficulty = {
            diff: sum(vals) / len(vals)
            for diff, vals in reward_by_diff.items()
        }

        # ---------- steps to solve (successful episodes only) ----------
        solved = [m for m in history if m.was_bug_fixed]
        avg_steps_to_solve: Optional[float] = (
            sum(m.total_steps for m in solved) / len(solved) if solved else None
        )

        # ---------- success rate overall ----------
        success_rate = len(solved) / total

        # ---------- success rate by difficulty ----------
        success_by_diff: Dict[str, List[bool]] = defaultdict(list)
        for m in history:
            success_by_diff[m.difficulty].append(m.was_bug_fixed)
        success_rate_by_difficulty = {
            diff: sum(flags) / len(flags)
            for diff, flags in success_by_diff.items()
        }

        # ---------- success rate by bug type ----------
        success_by_bug: Dict[str, List[bool]] = defaultdict(list)
        for m in history:
            success_by_bug[m.bug_type].append(m.was_bug_fixed)
        success_rate_by_bug_type = {
            bug: sum(flags) / len(flags)
            for bug, flags in success_by_bug.items()
        }

        # ---------- avg regression count ----------
        avg_regression_count = sum(m.regression_count for m in history) / total

        # ---------- recent trend ----------
        recent_trend: Optional[float] = None
        if total >= 40:
            recent_20 = history[-20:]
            prev_20 = history[-40:-20]
            recent_trend = (
                sum(m.final_reward for m in recent_20) / 20
                - sum(m.final_reward for m in prev_20) / 20
            )

        return {
            "total_episodes": total,
            "avg_reward": avg_reward,
            "avg_reward_by_difficulty": avg_reward_by_difficulty,
            "avg_steps_to_solve": avg_steps_to_solve,
            "success_rate": success_rate,
            "success_rate_by_difficulty": success_rate_by_difficulty,
            "success_rate_by_bug_type": success_rate_by_bug_type,
            "avg_regression_count": avg_regression_count,
            "recent_trend": recent_trend,
        }
