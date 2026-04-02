"""
SQL Debugger Environment — Core logic.

Implements the OpenEnv Environment interface for SQL query debugging.
Supports both static tasks (predefined bugs) and dynamic tasks (random bug injection).
"""

from __future__ import annotations

import uuid
from typing import Any, Optional

from openenv.core.env_server.interfaces import Environment

from ..models import SQLAction, SQLObservation, SQLState
from .bug_injector import inject_bug, InjectedBug
from .grader import SQLGrader
from .sql_engine import SQLiteEngine
from .tasks import ALL_TASKS, SQLTask, get_task_by_index


class SQLDebuggerEnv(Environment):
    """SQL Query Debugger environment.

    The agent receives a broken SQL query, database schema, and expected output.
    It must iteratively fix the query by submitting corrected versions.

    For static tasks (seeds 0-8): uses predefined broken queries.
    For dynamic tasks (seeds 9+): injects random bugs into correct queries,
    making every episode unique.
    """

    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(self):
        super().__init__()
        self._engine: Optional[SQLiteEngine] = None
        self._grader = SQLGrader()
        self._state = SQLState()
        self._current_task: Optional[SQLTask] = None
        self._current_broken_query: str = ""
        self._current_bug: Optional[InjectedBug] = None
        self._best_reward: float = 0.0
        self._hint_general: str = ""
        self._hint_specific: str = ""

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
                  None: random task with random bug.
        """
        if seed is not None:
            task = get_task_by_index(seed)
        else:
            import random
            task = random.choice(ALL_TASKS)
            seed = random.randint(0, 999999)

        self._current_task = task
        self._best_reward = 0.0

        # Bug injection: always dynamic when seed > 100, use static for low seeds
        # This ensures reproducible baseline (seeds 0-8) AND variety for evaluation
        use_static = task.broken_query is not None and seed is not None and seed < 100

        if use_static:
            self._current_broken_query = task.broken_query
            self._current_bug = None
            self._hint_general = task.hint_general
            self._hint_specific = task.hint_specific
        else:
            # Dynamic bug injection — every seed produces a unique broken query
            broken, bug = inject_bug(task.correct_query, task.difficulty, seed=seed)
            self._current_broken_query = broken
            self._current_bug = bug
            self._hint_general = bug.hint_general
            self._hint_specific = bug.hint_specific

        # Create fresh SQLite engine
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
            return self._hint_general or f"Check your query against the schema."
        else:
            return self._hint_specific or self._hint_general or f"Review the error message carefully."
