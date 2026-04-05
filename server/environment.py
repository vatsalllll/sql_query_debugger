"""
SQL Debugger Environment — Core logic.

Implements the OpenEnv Environment interface for SQL query debugging.
Integrates composable rubrics, adaptive curriculum, multi-agent coordination,
and episode analytics for rich RL training signals.
"""

from __future__ import annotations

import random
import uuid
from typing import Any, Dict, List, Optional

from openenv.core.env_server.interfaces import Environment

from ..models import SQLAction, SQLObservation, SQLState
from .analytics import AnalyticsCollector
from .bug_injector import InjectedBug, inject_bug, inject_multi_bug
from .curriculum import CurriculumManager
from .multi_agent import SessionCoordinator
from .rubrics import CompositeRubric
from .sql_engine import SQLiteEngine
from .tasks import ALL_TASKS, SQLTask, get_task_by_index


class SQLDebuggerEnv(Environment):
    """SQL Query Debugger environment.

    The agent receives a broken SQL query, database schema, and expected output.
    It must iteratively fix the query by submitting corrected versions.

    Features:
      - Composable reward rubrics with full decomposition
      - Adaptive curriculum (when seed=None)
      - Multi-agent competitive/collaborative modes (via group_id kwarg)
      - Episode analytics and training observability
    """

    SUPPORTS_CONCURRENT_SESSIONS = True

    # Shared across instances for multi-agent coordination and analytics
    _coordinator = SessionCoordinator()
    _analytics = AnalyticsCollector()
    _curriculum = CurriculumManager()

    def __init__(self) -> None:
        super().__init__()
        self._engine: Optional[SQLiteEngine] = None
        self._rubric = CompositeRubric()
        self._state = SQLState()
        self._current_task: Optional[SQLTask] = None
        self._current_broken_query: str = ""
        self._current_bug: Optional[InjectedBug] = None
        self._current_bugs: List[InjectedBug] = []
        self._best_reward: float = 0.0
        self._hint_general: str = ""
        self._hint_specific: str = ""
        self._original_error: Optional[str] = None

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        **kwargs: Any,
    ) -> SQLObservation:
        """Start a new debugging episode.

        Args:
            seed: Task selection + bug injection seed.
                  Seeds 0-8: static tasks with predefined bugs.
                  Seeds 9+: dynamic tasks with randomly injected bugs.
                  None: curriculum-driven random task.
            **kwargs:
                group_id: Multi-agent group identifier.
                mode: Multi-agent mode ("competitive" or "collaborative").
        """
        group_id = kwargs.get("group_id", "")
        agent_mode = kwargs.get("mode", "")

        if seed is not None:
            task = get_task_by_index(seed)
        else:
            # Curriculum-driven difficulty selection
            difficulty = self._curriculum.select_difficulty()
            tasks_at_level = [t for t in ALL_TASKS if t.difficulty == difficulty]
            task = random.choice(tasks_at_level) if tasks_at_level else random.choice(ALL_TASKS)
            seed = random.randint(0, 999999)

        self._current_task = task
        self._best_reward = 0.0
        self._current_bugs = []

        # Bug injection: static for low seeds, dynamic otherwise
        use_static = task.broken_query is not None and seed is not None and seed < 100

        if use_static:
            self._current_broken_query = task.broken_query
            self._current_bug = None
            self._hint_general = task.hint_general
            self._hint_specific = task.hint_specific
        elif self._curriculum.is_expert_mode and seed is not None and seed >= 100:
            # Expert mode: inject multiple bugs
            broken, bugs = inject_multi_bug(
                task.correct_query, task.difficulty, num_bugs=2, seed=seed,
            )
            self._current_broken_query = broken
            self._current_bugs = bugs
            self._current_bug = bugs[0] if bugs else None
            self._hint_general = bugs[0].hint_general if bugs else ""
            self._hint_specific = f"Multiple bugs ({len(bugs)}) — fix them one at a time."
        else:
            # Dynamic single-bug injection
            broken, bug = inject_bug(task.correct_query, task.difficulty, seed=seed)
            self._current_broken_query = broken
            self._current_bug = bug
            self._hint_general = bug.hint_general
            self._hint_specific = bug.hint_specific

        # Create fresh SQLite engine and capture original error
        self._engine = SQLiteEngine()
        self._engine.setup(task.schema_sql, task.seed_data_sql)
        _, self._original_error = self._engine.execute(self._current_broken_query)

        # Initialize state
        ep_id = episode_id or str(uuid.uuid4())
        self._state = SQLState(
            episode_id=ep_id,
            step_count=0,
            task_id=task.task_id,
            difficulty=task.difficulty,
            best_reward=0.0,
            current_query="",
            group_id=group_id,
            agent_mode=agent_mode,
        )

        # Analytics: start tracking
        bug_type = self._current_bug.bug_type if self._current_bug else "static"
        self._analytics.start_episode(
            episode_id=ep_id,
            task_id=task.task_id,
            difficulty=task.difficulty,
            bug_type=bug_type,
        )

        # Multi-agent: register session
        if group_id:
            self._coordinator.register_session(
                session_id=ep_id,
                group_id=group_id,
                mode=agent_mode,
                seed=seed,
            )

        # Build metadata
        metadata: Dict[str, Any] = {
            "curriculum": self._curriculum.get_info(),
        }
        if group_id:
            metadata["multi_agent"] = self._coordinator.get_group_info(ep_id) or {}

        return SQLObservation(
            done=False,
            reward=0.0,
            metadata=metadata,
            task_id=task.task_id,
            difficulty=task.difficulty,
            broken_query=self._current_broken_query,
            schema_description=task.schema_sql.strip(),
            expected_output=self._format_rows(task.expected_output),
            execution_result="",
            execution_error="",
            hint=f"Task: {task.description}",
            steps_remaining=task.max_steps,
        )

    def step(
        self,
        action: SQLAction,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> SQLObservation:
        """Execute the agent's SQL query and grade it."""
        if not isinstance(action, SQLAction):
            raise ValueError(f"Expected SQLAction, got {type(action)}")

        if self._current_task is None:
            raise RuntimeError("Environment not reset. Call reset() first.")

        task = self._current_task
        self._state.step_count += 1
        self._state.current_query = action.query

        # Execute query
        rows, error = self._engine.execute(action.query)

        # Grade with composable rubrics
        reward, done, components = self._rubric.grade(
            actual_rows=rows,
            expected_rows=task.expected_output,
            execution_error=error,
            submitted_query=action.query,
            correct_query=task.correct_query,
            step_count=self._state.step_count,
            max_steps=task.max_steps,
            previous_best=self._best_reward,
            original_error=self._original_error,
        )

        # Track best reward (using raw correctness from components)
        correctness = components["correctness"]
        if correctness > self._best_reward:
            self._best_reward = correctness
        self._state.best_reward = self._best_reward

        # Multi-agent reward adjustment
        ep_id = self._state.episode_id
        if self._state.group_id:
            self._coordinator.record_step(
                session_id=ep_id,
                reward=reward,
                query=action.query,
                correctness=correctness,
            )
            ma_bonus = self._coordinator.compute_multi_agent_bonus(ep_id, reward)
            reward = max(-1.0, min(1.0, reward + ma_bonus))
            components["multi_agent_bonus"] = ma_bonus

        # Analytics: record step
        self._analytics.record_step(
            episode_id=ep_id,
            reward=reward,
            correctness=correctness,
            query=action.query,
            reward_components=components,
        )

        # Generate hint (with peer context in collaborative mode)
        hint = self._generate_hint(self._state.step_count, task, error)
        if self._state.group_id and self._state.agent_mode == "collaborative":
            peer_ctx = self._coordinator.get_peer_context(ep_id)
            if peer_ctx and peer_ctx.peer_best_query:
                hint += f"\n[Peer's best attempt]: {peer_ctx.peer_best_query[:100]}"

        # Format execution result
        if error:
            exec_result = ""
        else:
            exec_result = self._format_rows(rows) if rows else "(empty result set)"

        # Build metadata
        metadata: Dict[str, Any] = {
            "reward_components": components,
            "curriculum": self._curriculum.get_info(),
        }
        if self._state.group_id:
            metadata["multi_agent"] = self._coordinator.get_group_info(ep_id) or {}

        # On episode end: finalize analytics and record curriculum
        if done:
            episode_metrics = self._analytics.finish_episode(ep_id)
            metadata["analytics"] = {
                "total_steps": episode_metrics.total_steps,
                "final_reward": episode_metrics.final_reward,
                "regression_count": episode_metrics.regression_count,
                "was_bug_fixed": episode_metrics.was_bug_fixed,
                "unique_queries": episode_metrics.unique_queries_submitted,
            }
            self._curriculum.record_episode(task.difficulty, reward)

            # Multi-agent cleanup
            if self._state.group_id:
                self._coordinator.unregister_session(ep_id)

        return SQLObservation(
            done=done,
            reward=reward,
            metadata=metadata,
            task_id=task.task_id,
            difficulty=task.difficulty,
            broken_query=self._current_broken_query,
            schema_description=task.schema_sql.strip(),
            expected_output=self._format_rows(task.expected_output),
            execution_result=exec_result,
            execution_error=error or "",
            hint=hint,
            steps_remaining=max(0, task.max_steps - self._state.step_count),
        )

    @property
    def state(self) -> SQLState:
        """Get current environment state."""
        return self._state

    def close(self) -> None:
        """Clean up SQLite connections."""
        if self._engine and self._engine._conn:
            self._engine._conn.close()
            self._engine = None

    @staticmethod
    def _format_rows(rows: list) -> str:
        """Format rows as a readable string."""
        if not rows:
            return "(empty)"
        lines = [str(row) for row in rows]
        return "\n".join(lines)

    def _generate_hint(self, step_count: int, task: SQLTask, last_error: Optional[str]) -> str:
        """Generate progressive hints based on step count."""
        if step_count <= 2:
            return f"Task: {task.description}"
        elif step_count <= 3:
            return self._hint_general or "Check your query against the schema."
        else:
            return self._hint_specific or self._hint_general or "Review the error message carefully."
