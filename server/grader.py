"""
SQL Debugger Grader — Multi-signal reward function.

Provides partial progress signals for GRPO-compatible training:
1. Result correctness (0.0 - 1.0)
2. Efficiency bonus (0.0 - 0.2)
3. Progress bonus (+0.05)
"""

from __future__ import annotations

from typing import List, Optional, Tuple


class SQLGrader:
    """Deterministic grader for SQL query results."""

    def grade(
        self,
        actual_rows: Optional[List[tuple]],
        expected_rows: List[tuple],
        execution_error: Optional[str],
        step_count: int,
        max_steps: int,
        previous_best: float,
    ) -> Tuple[float, bool]:
        """
        Grade a query attempt.

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
        if execution_error is not None:
            return 0.0

        if actual_rows is None:
            return 0.0

        if len(expected_rows) == 0:
            return 1.0 if len(actual_rows) == 0 else 0.05

        if len(actual_rows) == 0:
            return 0.05

        # Check column count matches
        if len(actual_rows[0]) != len(expected_rows[0]):
            return 0.1

        # Normalize rows for comparison (handle float precision)
        actual_normalized = set(self._normalize_row(r) for r in actual_rows)
        expected_normalized = set(self._normalize_row(r) for r in expected_rows)

        if actual_normalized == expected_normalized:
            return 1.0

        # Partial match: fraction of expected rows found
        matching = actual_normalized & expected_normalized
        partial_score = len(matching) / len(expected_normalized)

        # Scale partial score between 0.1 and 0.9
        return 0.1 + (partial_score * 0.8)

    def _compute_efficiency(self, step_count: int, max_steps: int) -> float:
        """Bonus for solving in fewer steps. Returns 0.0 - 0.2."""
        if max_steps <= 0:
            return 0.0
        return max(0.0, 0.2 * (1.0 - step_count / max_steps))

    @staticmethod
    def _normalize_row(row: tuple) -> tuple:
        """Normalize a row for comparison — round floats to 2 decimal places."""
        return tuple(
            round(v, 2) if isinstance(v, float) else v
            for v in row
        )

    def _compute_progress(self, correctness: float, previous_best: float) -> float:
        """Bonus for improving over previous best attempt. Returns 0.0 or 0.05."""
        if correctness > previous_best:
            return 0.05
        return 0.0
