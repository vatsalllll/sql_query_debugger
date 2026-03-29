"""
SQL Debugger Environment — Core logic.

Implements the OpenEnv Environment interface for SQL query debugging.
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from openenv.core.env_server.interfaces import Environment

from ..models import SQLAction, SQLObservation, SQLState
from .grader import SQLGrader
from .sql_engine import SQLiteEngine
from .tasks import ALL_TASKS, SQLTask, get_task_by_index


class SQLDebuggerEnv(Environment):
    """SQL Query Debugger environment.

    The agent receives a broken SQL query, database schema, and expected output.
    It must iteratively fix the query by submitting corrected versions.
    """

    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self):
        super().__init__()
        self._engine: Optional[SQLiteEngine] = None
        self._grader = SQLGrader()
        self._state = SQLState()
        self._current_task: Optional[SQLTask] = None
        self._best_reward: float = 0.0

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        **kwargs: Any,
    ) -> SQLObservation:
        """Start a new debugging episode with a broken SQL task."""
        # Pick task deterministically from seed, or randomly
        if seed is not None:
            task = get_task_by_index(seed)
        else:
            import random
            task = random.choice(ALL_TASKS)

        self._current_task = task
        self._best_reward = 0.0

        # Create fresh SQLite engine for each episode (thread-safe)
        self._engine = SQLiteEngine()
        self._engine.setup(task.schema_sql, task.seed_data_sql)

        # Initialize state
        self._state = SQLState(
            episode_id=episode_id or str(uuid.uuid4()),
            step_count=0,
            task_id=task.task_id,
            difficulty=task.difficulty,
            best_reward=0.0,
            current_query="",
        )

        return SQLObservation(
            done=False,
            reward=0.0,
            task_id=task.task_id,
            difficulty=task.difficulty,
            broken_query=task.broken_query,
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

        # Grade
        reward, done = self._grader.grade(
            actual_rows=rows,
            expected_rows=task.expected_output,
            execution_error=error,
            step_count=self._state.step_count,
            max_steps=task.max_steps,
            previous_best=self._best_reward,
        )

        # Track best reward
        correctness = self._grader._compute_correctness(rows, task.expected_output, error)
        if correctness > self._best_reward:
            self._best_reward = correctness
        self._state.best_reward = self._best_reward

        # Generate hint
        hint = self._generate_hint(self._state.step_count, task, error)

        # Format execution result
        if error:
            exec_result = ""
        else:
            exec_result = self._format_rows(rows) if rows else "(empty result set)"

        return SQLObservation(
            done=done,
            reward=reward,
            task_id=task.task_id,
            difficulty=task.difficulty,
            broken_query=task.broken_query,
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

    @staticmethod
    def _format_rows(rows: list) -> str:
        """Format rows as a readable string."""
        if not rows:
            return "(empty)"
        lines = [str(row) for row in rows]
        return "\n".join(lines)

    @staticmethod
    def _generate_hint(step_count: int, task: SQLTask, last_error: Optional[str]) -> str:
        """Generate progressive hints based on step count."""
        if step_count <= 2:
            return f"Task: {task.description}"
        elif step_count <= 3:
            return task.hint_general
        else:
            return task.hint_specific
