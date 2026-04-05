"""
Multi-Agent Session Coordinator
---------------------------------
Manages competitive and collaborative multi-agent sessions.

Modes:
  competitive ("race") — Agents race to fix the same query. First solver gets a time bonus.
  collaborative ("relay") — Agents take turns. Each sees the previous agent's best attempt.
"""

from __future__ import annotations

import time
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PeerContext:
    """Context from other agents in the same group."""

    num_peers: int
    peer_best_reward: float
    peer_best_query: Optional[str] = None   # Only shared in collaborative mode
    peer_hints: List[str] = field(default_factory=list)
    is_first_solver: bool = False
    rank: int = 0  # 0 = not yet ranked


@dataclass
class AgentSession:
    """Tracks a single agent's state within a group."""

    session_id: str
    group_id: str
    best_reward: float = 0.0
    best_query: str = ""
    step_count: int = 0
    solved: bool = False
    solve_time: Optional[float] = None  # Time of first correct solution
    hints_generated: List[str] = field(default_factory=list)


@dataclass
class TaskGroup:
    """A group of agents working on the same task."""

    group_id: str
    mode: str  # "competitive" or "collaborative"
    seed: int
    created_at: float = field(default_factory=time.monotonic)
    agent_sessions: Dict[str, AgentSession] = field(default_factory=dict)
    first_solver_id: Optional[str] = None
    solve_order: List[str] = field(default_factory=list)  # Order of solving agents


class SessionCoordinator:
    """Thread-safe coordinator for multi-agent sessions.

    Manages task groups where multiple agents work on the same broken SQL query
    in either competitive ("race") or collaborative ("relay") mode.

    Thread safety is guaranteed via a single reentrant lock that protects all
    state mutations and reads of shared group/session data.
    """

    COMPETITIVE_FIRST_BONUS = 0.1    # Bonus for first solver
    COMPETITIVE_RANK_DECAY = 0.03    # Bonus decreases per rank position
    COLLABORATIVE_SHARE_FACTOR = 1.0 # All agents share reward equally

    def __init__(self) -> None:
        self._groups: Dict[str, TaskGroup] = {}
        self._session_to_group: Dict[str, str] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register_session(
        self,
        session_id: str,
        group_id: str,
        mode: str,
        seed: int,
    ) -> None:
        """Register an agent session in a task group. Creates group if needed.

        If the group already exists its mode and seed are preserved; the new
        agent is simply appended to the existing group.  Registering the same
        session_id twice replaces the previous registration silently.

        Args:
            session_id: Unique identifier for the agent session.
            group_id:   Identifier shared by all agents on the same task.
            mode:       "competitive" or "collaborative".
            seed:       Task seed so agents work on the same broken query.
        """
        with self._lock:
            # Create group on first registration
            if group_id not in self._groups:
                self._groups[group_id] = TaskGroup(
                    group_id=group_id,
                    mode=mode,
                    seed=seed,
                )

            group = self._groups[group_id]

            # Detach session from any previous group it belonged to
            old_group_id = self._session_to_group.get(session_id)
            if old_group_id and old_group_id != group_id:
                old_group = self._groups.get(old_group_id)
                if old_group:
                    old_group.agent_sessions.pop(session_id, None)
                    if not old_group.agent_sessions:
                        del self._groups[old_group_id]

            session = AgentSession(session_id=session_id, group_id=group_id)
            group.agent_sessions[session_id] = session
            self._session_to_group[session_id] = group_id

    def record_step(
        self,
        session_id: str,
        reward: float,
        query: str,
        correctness: float,
    ) -> None:
        """Record an agent's step result.

        Updates the session's best reward and query when the current step
        achieves a new personal best.  Marks the session as solved (and records
        solve time + solve order on the group) when correctness reaches 1.0 for
        the first time.

        Silently ignores calls for unknown session_ids.

        Args:
            session_id:  Session that took the step.
            reward:      Scalar reward received at this step.
            query:       The SQL query submitted at this step.
            correctness: Fraction of expected rows matched [0.0, 1.0].
        """
        with self._lock:
            session, group = self._get_session_and_group(session_id)
            if session is None or group is None:
                return

            session.step_count += 1

            if correctness > session.best_reward:
                session.best_reward = correctness
                session.best_query = query

            # Mark as solved on first correct answer
            if correctness >= 1.0 and not session.solved:
                session.solved = True
                session.solve_time = time.monotonic()

                # Register solve order on the group
                if group.first_solver_id is None:
                    group.first_solver_id = session_id
                if session_id not in group.solve_order:
                    group.solve_order.append(session_id)

    def get_peer_context(self, session_id: str) -> Optional[PeerContext]:
        """Get context about other agents in the same group.

        Returns None if the session is not registered in any group.

        In competitive mode the peers' best queries are withheld; only the
        scalar peer_best_reward is shared so agents can gauge relative progress
        without copying each other's answers.

        In collaborative mode the best query is also shared so each agent can
        build on the group's collective best attempt.

        Args:
            session_id: The requesting agent's session identifier.

        Returns:
            A PeerContext describing the rest of the group, or None.
        """
        with self._lock:
            session, group = self._get_session_and_group(session_id)
            if session is None or group is None:
                return None

            peers = [
                s for sid, s in group.agent_sessions.items()
                if sid != session_id
            ]

            if not peers:
                # Single-agent group — return a context with zeroed peer info
                return PeerContext(
                    num_peers=0,
                    peer_best_reward=0.0,
                    peer_best_query=None,
                    peer_hints=[],
                    is_first_solver=session.solved and group.first_solver_id == session_id,
                    rank=self._compute_rank(session_id, group),
                )

            peer_best_reward = max(p.best_reward for p in peers)
            peer_hints: List[str] = []
            for p in peers:
                peer_hints.extend(p.hints_generated)

            # Best query among peers (agent with highest correctness)
            best_peer = max(peers, key=lambda p: p.best_reward)

            if group.mode == "collaborative":
                peer_best_query: Optional[str] = best_peer.best_query or None
            else:
                # competitive — do NOT share queries
                peer_best_query = None

            return PeerContext(
                num_peers=len(peers),
                peer_best_reward=peer_best_reward,
                peer_best_query=peer_best_query,
                peer_hints=peer_hints,
                is_first_solver=(
                    session.solved and group.first_solver_id == session_id
                ),
                rank=self._compute_rank(session_id, group),
            )

    def compute_multi_agent_bonus(
        self,
        session_id: str,
        base_reward: float,
    ) -> float:
        """Compute reward adjustment based on multi-agent dynamics.

        Competitive mode
        ----------------
        * First solver receives COMPETITIVE_FIRST_BONUS.
        * Subsequent solvers receive a decaying bonus:
          ``COMPETITIVE_FIRST_BONUS - rank * COMPETITIVE_RANK_DECAY``
          (floored at 0.0 so late solvers never receive a negative bonus).
        * Agents that have not yet solved the task receive no bonus.

        Collaborative mode
        ------------------
        * All agents share the group's collective best reward equally, scaled
          by COLLABORATIVE_SHARE_FACTOR.  The adjustment is the difference
          between the shared group reward and the agent's own base_reward.
          This can be positive (agent is below group best) or negative (agent
          already exceeds group best — rare, but clipped at 0.0 to avoid
          penalising strong individual performance).

        Returns 0.0 for unknown session_ids or single-agent groups.

        Args:
            session_id:  The agent requesting the bonus computation.
            base_reward: The agent's raw reward for the current step.

        Returns:
            Signed float representing the reward adjustment.
        """
        with self._lock:
            session, group = self._get_session_and_group(session_id)
            if session is None or group is None:
                return 0.0

            peers = [
                s for sid, s in group.agent_sessions.items()
                if sid != session_id
            ]

            if not peers:
                # Single-agent group — no multi-agent dynamics apply
                return 0.0

            if group.mode == "competitive":
                if not session.solved:
                    return 0.0
                rank = self._compute_rank(session_id, group)
                if rank == 0:
                    # Not yet ranked — shouldn't happen when solved=True, but guard
                    return 0.0
                bonus = self.COMPETITIVE_FIRST_BONUS - (rank - 1) * self.COMPETITIVE_RANK_DECAY
                return max(0.0, bonus)

            else:  # collaborative
                all_sessions = list(group.agent_sessions.values())
                group_best = max(s.best_reward for s in all_sessions)
                shared_reward = group_best * self.COLLABORATIVE_SHARE_FACTOR
                adjustment = shared_reward - base_reward
                # Never penalise an agent whose individual performance exceeds group best
                return max(0.0, adjustment)

    def unregister_session(self, session_id: str) -> None:
        """Remove an agent from its group. Clean up empty groups.

        Silently ignores unknown session_ids.

        Args:
            session_id: The session to remove.
        """
        with self._lock:
            group_id = self._session_to_group.pop(session_id, None)
            if group_id is None:
                return

            group = self._groups.get(group_id)
            if group is None:
                return

            group.agent_sessions.pop(session_id, None)

            # Patch solve_order if the departing agent was recorded there
            if session_id in group.solve_order:
                group.solve_order.remove(session_id)

            # Reset first_solver_id if the departing agent held it
            if group.first_solver_id == session_id:
                group.first_solver_id = group.solve_order[0] if group.solve_order else None

            # Remove the group entirely if no agents remain
            if not group.agent_sessions:
                del self._groups[group_id]

    def get_group_info(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get group status for observability metadata.

        Returns a snapshot dict suitable for logging or API responses.
        Returns None if the session is not registered.

        Args:
            session_id: Any registered session belonging to the group.

        Returns:
            Dict with keys:
              - group_id (str)
              - mode (str)
              - seed (int)
              - num_agents (int)
              - first_solver_id (str | None)
              - solve_order (List[str])
              - agents (List[Dict]): per-agent summary dicts containing
                session_id, best_reward, step_count, solved, rank.
              - group_best_reward (float)
              - elapsed_s (float): seconds since group creation.
        """
        with self._lock:
            session, group = self._get_session_and_group(session_id)
            if session is None or group is None:
                return None

            agent_summaries = []
            for sid, s in group.agent_sessions.items():
                agent_summaries.append({
                    "session_id": sid,
                    "best_reward": s.best_reward,
                    "step_count": s.step_count,
                    "solved": s.solved,
                    "rank": self._compute_rank(sid, group),
                })

            all_rewards = [s.best_reward for s in group.agent_sessions.values()]
            group_best = max(all_rewards) if all_rewards else 0.0

            return {
                "group_id": group.group_id,
                "mode": group.mode,
                "seed": group.seed,
                "num_agents": len(group.agent_sessions),
                "first_solver_id": group.first_solver_id,
                "solve_order": list(group.solve_order),
                "agents": agent_summaries,
                "group_best_reward": group_best,
                "elapsed_s": time.monotonic() - group.created_at,
            }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _get_session_and_group(
        self,
        session_id: str,
    ) -> tuple[Optional[AgentSession], Optional[TaskGroup]]:
        """Return (AgentSession, TaskGroup) for a session_id, or (None, None).

        Must be called while holding self._lock.
        """
        group_id = self._session_to_group.get(session_id)
        if group_id is None:
            return None, None

        group = self._groups.get(group_id)
        if group is None:
            return None, None

        session = group.agent_sessions.get(session_id)
        if session is None:
            return None, None

        return session, group

    @staticmethod
    def _compute_rank(session_id: str, group: TaskGroup) -> int:
        """Return the 1-based solve rank for a session, or 0 if not yet solved.

        Position 1 = first to solve.

        Must be called while holding the coordinator lock.
        """
        try:
            return group.solve_order.index(session_id) + 1
        except ValueError:
            return 0
