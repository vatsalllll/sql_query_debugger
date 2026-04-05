"""
SQL Debugger Environment — Pydantic Models
-------------------------------------------
Defines Action, Observation, and State types for the SQL debugging environment.

The metadata dict on SQLObservation carries rich training signals:
  - reward_components: Decomposed reward (correctness, efficiency, quality, diagnostic)
  - curriculum: Current curriculum level and stats
  - multi_agent: Peer context in multi-agent sessions
  - analytics: Episode summary on completion
"""

from __future__ import annotations

from typing import Optional

from pydantic import field_validator
from openenv.core.env_server.types import Action, Observation, State


class SQLAction(Action):
    """Agent submits a SQL query to fix the broken one."""

    query: str

    @field_validator("query")
    @classmethod
    def query_must_not_be_empty(cls, v: str) -> str:
        """Reject empty or whitespace-only queries."""
        if not v or not v.strip():
            raise ValueError("Query must not be empty or whitespace-only.")
        return v.strip()


class SQLObservation(Observation):
    """Observation returned after each step.

    The inherited `metadata: Dict[str, Any]` field carries additional training signals:
      - reward_components: Individual reward scores (correctness, efficiency, etc.)
      - curriculum: Adaptive difficulty state
      - multi_agent: Peer context when in multi-agent mode
      - analytics: Episode summary (only on done=True)
    """

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
    group_id: str = ""
    agent_mode: str = ""  # "", "competitive", "collaborative"
