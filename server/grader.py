"""
SQL Debugger Grader — Backward-compatible wrapper.

Delegates to the composable rubric system in rubrics.py while maintaining
the original grade() call signature used by older code and the Gradio UI.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from .rubrics import CompositeRubric, CorrectnessRubric


class SQLGrader:
    """Backward-compatible grader that delegates to CompositeRubric.

    This class preserves the original grade() signature so that code
    which depends on SQLGrader (e.g. the Gradio UI) continues to work
    without modification.
    """

    def __init__(self) -> None:
        self._rubric = CompositeRubric()
        self._correctness = CorrectnessRubric()

    def grade(
        self,
        actual_rows: Optional[List[tuple]],
        expected_rows: List[tuple],
        execution_error: Optional[str],
        step_count: int,
        max_steps: int,
        previous_best: float,
    ) -> Tuple[float, bool]:
        """Grade a query attempt (legacy interface).

        Returns:
            (reward, done) tuple where reward is 0.0-1.0 and done indicates episode end.
        """
        correctness = self._compute_correctness(actual_rows, expected_rows, execution_error)
        efficiency = self._compute_efficiency(step_count, max_steps)
        progress = self._compute_progress(correctness, previous_best)

        reward = min(1.0, correctness + efficiency + progress)
        done = correctness == 1.0 or step_count >= max_steps

        return reward, done

    def _compute_correctness(
        self,
        actual_rows: Optional[List[tuple]],
        expected_rows: List[tuple],
        execution_error: Optional[str],
    ) -> float:
        """Compare query results against expected output. Returns 0.0 - 1.0."""
        return self._correctness.score(actual_rows, expected_rows, execution_error)

    def _compute_efficiency(self, step_count: int, max_steps: int) -> float:
        """Bonus for solving in fewer steps. Returns 0.0 - 0.2."""
        if max_steps <= 0:
            return 0.0
        return max(0.0, 0.2 * (1.0 - step_count / max_steps))

    @staticmethod
    def _normalize_row(row: tuple) -> tuple:
        """Normalize a row for comparison."""
        return tuple(
            round(v, 2) if isinstance(v, float) else v
            for v in row
        )

    def _compute_progress(self, correctness: float, previous_best: float) -> float:
        """Bonus for improving over previous best attempt."""
        if correctness > previous_best:
            return 0.05
        return 0.0
