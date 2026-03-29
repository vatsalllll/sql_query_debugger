"""
SQL Debugger Client
-------------------
Client-side wrapper for the SQL Debugger environment server.
"""

from __future__ import annotations

from openenv.core.client_types import StepResult
from openenv.core.env_client import EnvClient

from .models import SQLAction, SQLObservation, SQLState


class SQLDebuggerClient(EnvClient[SQLAction, SQLObservation, SQLState]):

    def _step_payload(self, action: SQLAction) -> dict:
        return {"query": action.query}

    def _parse_result(self, payload: dict) -> StepResult[SQLObservation]:
        obs = SQLObservation(**payload["observation"])
        return StepResult(
            observation=obs,
            reward=payload.get("reward"),
            done=bool(payload.get("done", False)),
        )

    def _parse_state(self, payload: dict) -> SQLState:
        return SQLState(
            episode_id=payload.get("episode_id"),
            step_count=payload.get("step_count", 0),
            task_id=payload.get("task_id", ""),
            difficulty=payload.get("difficulty", ""),
            best_reward=payload.get("best_reward", 0.0),
            current_query=payload.get("current_query", ""),
        )
