"""
SQL Debugger Environment — Pydantic Models
-------------------------------------------
Defines Action, Observation, and State types for the SQL debugging environment.
"""

from __future__ import annotations

from typing import Optional

from openenv.core.env_server.types import Action, Observation, State


class SQLAction(Action):
    """Agent submits a SQL query to fix the broken one."""

    query: str


class SQLObservation(Observation):
    """Observation returned after each step."""

    # Inherits: done: bool, reward: Optional[float], metadata: Dict[str, Any]
    task_id: str = ""
    difficulty: str = ""
    broken_query: str = ""
    schema_description: str = ""
    expected_output: str = ""
    execution_result: str = ""
    execution_error: str = ""
    hint: str = ""
    steps_remaining: int = 0


class SQLState(State):
    """Internal environment state."""

    # Inherits: episode_id: Optional[str], step_count: int
    task_id: str = ""
    difficulty: str = ""
    best_reward: float = 0.0
    current_query: str = ""
