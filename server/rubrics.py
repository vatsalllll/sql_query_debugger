"""
SQL Debugger — Composable Reward Rubrics.

Reward decomposition philosophy
--------------------------------
Rather than collapsing all quality signals into a single scalar, each rubric
is responsible for exactly one aspect of query correctness or quality.  A
CompositeRubric then assembles those scalars into a weighted total reward.

This separation has two practical benefits for RL training:

1. **Interpretability** — the ``components`` dict returned by
   ``CompositeRubric.grade()`` lets you log exactly which signal is
   driving (or blocking) learning.

2. **Curriculum control** — weights can be adjusted per training phase
   (e.g. ignore quality signal early, ramp it up once correctness is
   stable) without touching rubric logic.

Rubric contract
---------------
Every rubric exposes a single ``score(...)`` method that returns a ``float``
in the range stated in its docstring.  Rubrics are pure functions of their
inputs — no side-effects, no shared state.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _normalize_row(row: tuple) -> tuple:
    """Round floats to 2 dp for stable comparison (mirrors SQLGrader)."""
    return tuple(round(v, 2) if isinstance(v, float) else v for v in row)


# ---------------------------------------------------------------------------
# 1. CorrectnessRubric
# ---------------------------------------------------------------------------

@dataclass
class CorrectnessRubric:
    """
    Compare query result rows against expected output.

    Returns a score in [0.0, 1.0]:
      - 1.0  exact match (set equality, or ordered match when ORDER BY present)
      - 0.1–0.9  partial match proportional to intersecting rows
      - 0.1  column count mismatch or empty actual when expected non-empty
      - 0.05  actual is empty / expected is empty but actual is not
      - 0.0  execution error or None result
    """

    def score(
        self,
        actual_rows: Optional[List[tuple]],
        expected_rows: List[tuple],
        execution_error: Optional[str],
        submitted_query: str = "",
    ) -> float:
        """
        Grade result rows.

        Parameters
        ----------
        actual_rows:
            Rows produced by executing the submitted query.  ``None`` means
            the query could not be executed.
        expected_rows:
            Ground-truth rows from the reference (correct) query.
        execution_error:
            Error string if execution failed; ``None`` on success.
        submitted_query:
            The SQL text of the submitted query.  When it contains an
            ORDER BY clause the comparison is order-sensitive.
        """
        if execution_error is not None:
            return 0.0

        if actual_rows is None:
            return 0.0

        if len(expected_rows) == 0:
            return 1.0 if len(actual_rows) == 0 else 0.05

        if len(actual_rows) == 0:
            return 0.05

        # Column count must match.
        if len(actual_rows[0]) != len(expected_rows[0]):
            return 0.1

        order_sensitive = self._has_order_by(submitted_query)

        if order_sensitive:
            return self._ordered_score(actual_rows, expected_rows)
        return self._set_score(actual_rows, expected_rows)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _has_order_by(query: str) -> bool:
        """Return True if *query* contains a top-level ORDER BY clause."""
        # Strip string literals to avoid false positives inside quoted text.
        cleaned = re.sub(r"'[^']*'", "''", query, flags=re.DOTALL)
        return bool(re.search(r"\bORDER\s+BY\b", cleaned, re.IGNORECASE))

    @staticmethod
    def _ordered_score(
        actual_rows: List[tuple],
        expected_rows: List[tuple],
    ) -> float:
        """Order-sensitive comparison; checks both content and sequence."""
        actual_norm = [_normalize_row(r) for r in actual_rows]
        expected_norm = [_normalize_row(r) for r in expected_rows]

        if actual_norm == expected_norm:
            return 1.0

        # Partial: count positional matches.
        matches = sum(a == e for a, e in zip(actual_norm, expected_norm))
        length_penalty = abs(len(actual_norm) - len(expected_norm)) / max(
            len(expected_norm), 1
        )
        partial = matches / max(len(expected_norm), 1) * (1.0 - length_penalty)
        return 0.1 + partial * 0.8

    @staticmethod
    def _set_score(
        actual_rows: List[tuple],
        expected_rows: List[tuple],
    ) -> float:
        """Order-insensitive (set) comparison."""
        actual_norm = set(_normalize_row(r) for r in actual_rows)
        expected_norm = set(_normalize_row(r) for r in expected_rows)

        if actual_norm == expected_norm:
            return 1.0

        matching = actual_norm & expected_norm
        partial = len(matching) / len(expected_norm)
        return 0.1 + partial * 0.8


# ---------------------------------------------------------------------------
# 2. EfficiencyRubric
# ---------------------------------------------------------------------------

@dataclass
class EfficiencyRubric:
    """
    Reward for solving the task in as few steps as possible.

    Score = max(0.0, 1.0 - step_count / max_steps).

    Step 1 → 1.0 (maximum efficiency)
    step == max_steps → 0.0
    """

    def score(self, step_count: int, max_steps: int) -> float:
        """
        Return an efficiency score in [0.0, 1.0].

        Parameters
        ----------
        step_count:
            Number of attempts made so far (1-indexed).
        max_steps:
            Episode budget.
        """
        if max_steps <= 0:
            return 0.0
        return max(0.0, 1.0 - step_count / max_steps)


# ---------------------------------------------------------------------------
# 3. QueryQualityRubric
# ---------------------------------------------------------------------------

@dataclass
class QueryQualityRubric:
    """
    Regex-based static analysis of SQL style and quality.

    Starts at 1.0 and applies deductions / bonuses:

    Deductions
    ----------
    -0.15  ``SELECT *`` when the correct query uses named columns
    -0.10  Missing table aliases in queries that JOIN 2+ tables
    -0.05  Inconsistent keyword casing (e.g. mixing ``SELECT`` and ``select``)

    Bonuses
    -------
    +0.10  Proper use of ``ROUND()`` or ``COALESCE()`` (capped at 1.0)

    All checks use the *correct_query* as a reference so that deductions
    are only applied when the canonical solution does not exhibit the
    same pattern.
    """

    def score(self, submitted_query: str, correct_query: str) -> float:
        """
        Return a quality score in [0.0, 1.0].

        Parameters
        ----------
        submitted_query:
            The SQL text to evaluate.
        correct_query:
            The reference solution (used for contextual comparisons).
        """
        score = 1.0

        # --- SELECT * deduction ----------------------------------------
        if self._has_select_star(submitted_query) and not self._has_select_star(correct_query):
            score -= 0.15

        # --- Missing aliases deduction ----------------------------------
        if self._has_joins(submitted_query) and not self._has_table_aliases(submitted_query):
            score -= 0.10

        # --- Inconsistent casing deduction ------------------------------
        if self._has_mixed_casing(submitted_query):
            score -= 0.05

        # --- ROUND / COALESCE bonus -------------------------------------
        if self._uses_quality_functions(submitted_query) and self._uses_quality_functions(correct_query):
            score = min(1.0, score + 0.10)

        return max(0.0, score)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _strip_literals(query: str) -> str:
        """Remove quoted string literals to avoid false regex matches."""
        return re.sub(r"'[^']*'", "''", query, flags=re.DOTALL)

    def _has_select_star(self, query: str) -> bool:
        cleaned = self._strip_literals(query)
        return bool(re.search(r"\bSELECT\s+\*", cleaned, re.IGNORECASE))

    def _has_joins(self, query: str) -> bool:
        cleaned = self._strip_literals(query)
        return bool(re.search(r"\bJOIN\b", cleaned, re.IGNORECASE))

    def _has_table_aliases(self, query: str) -> bool:
        """
        Heuristic: look for at least one table alias pattern.

        Accepts both ``table_name alias`` and ``table_name AS alias``.
        """
        cleaned = self._strip_literals(query)
        # Pattern: identifier (optionally AS) identifier before JOIN/ON/WHERE/SET
        alias_pattern = re.compile(
            r"\b(?:FROM|JOIN)\s+\w+\s+(?:AS\s+)?\w+\b", re.IGNORECASE
        )
        return bool(alias_pattern.search(cleaned))

    def _has_mixed_casing(self, query: str) -> bool:
        """
        Detect inconsistent SQL keyword casing.

        Checks a representative set of common keywords.  If both an
        upper-case and a lower-case variant appear, the query is
        considered inconsistent.
        """
        query = self._strip_literals(query)
        keywords = ["select", "from", "where", "join", "order", "group", "having"]
        found_upper = False
        found_lower = False
        for kw in keywords:
            if re.search(rf"\b{kw}\b", query):
                found_lower = True
            if re.search(rf"\b{kw.upper()}\b", query):
                found_upper = True
            if found_upper and found_lower:
                return True
        return False

    @staticmethod
    def _uses_quality_functions(query: str) -> bool:
        cleaned = re.sub(r"'[^']*'", "''", query, flags=re.DOTALL)
        return bool(re.search(r"\b(ROUND|COALESCE)\s*\(", cleaned, re.IGNORECASE))


# ---------------------------------------------------------------------------
# 4. RegressionPenalty
# ---------------------------------------------------------------------------

@dataclass
class RegressionPenalty:
    """
    Compare current correctness against the agent's previous best.

    Returns
    -------
    +0.05  if correctness improved over previous_best
     0.0   if correctness equals previous_best
    -0.1   if correctness regressed below previous_best
    """

    def score(self, correctness: float, previous_best: float) -> float:
        """
        Return a regression adjustment in {-0.1, 0.0, +0.05}.

        Parameters
        ----------
        correctness:
            Correctness score for the current attempt (0.0–1.0).
        previous_best:
            Highest correctness score achieved in the episode so far.
        """
        if correctness > previous_best:
            return 0.05
        if correctness < previous_best:
            return -0.1
        return 0.0


# ---------------------------------------------------------------------------
# 5. DiagnosticRubric
# ---------------------------------------------------------------------------

@dataclass
class DiagnosticRubric:
    """
    Evaluate *how well* the agent fixed the bug, using execution metadata.

    Returns a score in {0.0, 0.3, 0.7, 1.0}:

    1.0  Query executed and results are correct — bug fully fixed.
    0.7  Query executed without error but returned wrong results — partial fix.
    0.3  Query raised a *different* error than the original broken query —
         the agent changed something relevant, even if not yet correct.
    0.0  Query raised the *same* error as the broken query — no progress.
    """

    def score(
        self,
        execution_error: Optional[str],
        correct_result: bool,
        original_error: Optional[str],
    ) -> float:
        """
        Return a diagnostic quality score in [0.0, 1.0].

        Parameters
        ----------
        execution_error:
            Error string from executing the submitted query; ``None`` on success.
        correct_result:
            ``True`` when the submitted query produced the expected rows.
        original_error:
            Error string from the original broken query (from bug metadata).
            ``None`` if the original query happened to execute without error.
        """
        if execution_error is None:
            # Executed cleanly.
            return 1.0 if correct_result else 0.7

        # Execution failed — compare error to the original.
        if original_error is not None and self._same_error(execution_error, original_error):
            return 0.0

        # Different error — agent changed something meaningful.
        return 0.3

    @staticmethod
    def _same_error(error_a: str, error_b: str) -> bool:
        """
        Coarse similarity check: compare the first ~60 chars of both errors.

        This avoids false negatives from line-number differences while still
        catching structurally identical error messages.
        """
        def _canonicalize(e: str) -> str:
            # Strip trailing whitespace and collapse internal whitespace.
            return re.sub(r"\s+", " ", e.strip()[:60]).lower()

        return _canonicalize(error_a) == _canonicalize(error_b)


# ---------------------------------------------------------------------------
# 6. CompositeRubric
# ---------------------------------------------------------------------------

DEFAULT_WEIGHTS: Dict[str, float] = {
    "correctness": 0.6,
    "efficiency": 0.15,
    "quality": 0.1,
    "diagnostic": 0.15,
}


@dataclass
class CompositeRubric:
    """
    Assemble individual rubric scores into a single weighted reward.

    The ``regression`` adjustment is applied *after* weighting as an
    additive term so that it can push the total reward above or below
    what the weighted sum would otherwise produce.

    Done condition
    --------------
    ``done`` is ``True`` when correctness reaches 1.0 (task solved) or
    step_count reaches max_steps (episode budget exhausted).

    Example
    -------
    >>> rubric = CompositeRubric()
    >>> reward, done, components = rubric.grade(
    ...     actual_rows=[(1, "Alice")],
    ...     expected_rows=[(1, "Alice")],
    ...     execution_error=None,
    ...     submitted_query="SELECT id, name FROM users",
    ...     correct_query="SELECT id, name FROM users",
    ...     step_count=2,
    ...     max_steps=10,
    ...     previous_best=0.0,
    ...     original_error="syntax error at or near ...",
    ... )
    """

    weights: Dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))

    # Rubric instances — created once, reused across calls.
    _correctness: CorrectnessRubric = field(default_factory=CorrectnessRubric, repr=False)
    _efficiency: EfficiencyRubric = field(default_factory=EfficiencyRubric, repr=False)
    _quality: QueryQualityRubric = field(default_factory=QueryQualityRubric, repr=False)
    _regression: RegressionPenalty = field(default_factory=RegressionPenalty, repr=False)
    _diagnostic: DiagnosticRubric = field(default_factory=DiagnosticRubric, repr=False)

    def grade(
        self,
        actual_rows: Optional[List[tuple]],
        expected_rows: List[tuple],
        execution_error: Optional[str],
        submitted_query: str,
        correct_query: str,
        step_count: int,
        max_steps: int,
        previous_best: float,
        original_error: Optional[str] = None,
    ) -> Tuple[float, bool, Dict[str, float]]:
        """
        Grade one agent attempt and return a full reward breakdown.

        Parameters
        ----------
        actual_rows:
            Rows returned by executing *submitted_query*.
        expected_rows:
            Ground-truth rows from the reference solution.
        execution_error:
            Execution error string, or ``None`` on success.
        submitted_query:
            The SQL text submitted by the agent.
        correct_query:
            The canonical reference SQL (used by quality rubric).
        step_count:
            1-indexed attempt number within the episode.
        max_steps:
            Maximum steps before the episode is forcibly ended.
        previous_best:
            Highest correctness score achieved so far in the episode.
        original_error:
            Error from the initial broken query (bug metadata); may be
            ``None`` if the original query ran without error.

        Returns
        -------
        total_reward : float
            Weighted sum of component scores, clamped to [−1.0, 1.0].
        done : bool
            ``True`` when the episode should terminate.
        components : Dict[str, float]
            Raw (un-weighted) score for every rubric, plus the final
            weighted total, for logging and curriculum analysis.
        """
        correctness = self._correctness.score(
            actual_rows, expected_rows, execution_error, submitted_query
        )
        efficiency = self._efficiency.score(step_count, max_steps)
        quality = self._quality.score(submitted_query, correct_query)
        regression = self._regression.score(correctness, previous_best)
        correct_result = correctness == 1.0
        diagnostic = self._diagnostic.score(execution_error, correct_result, original_error)

        w = self.weights
        weighted = (
            w.get("correctness", 0.0) * correctness
            + w.get("efficiency", 0.0) * efficiency
            + w.get("quality", 0.0) * quality
            + w.get("diagnostic", 0.0) * diagnostic
        )
        total_reward = max(0.01, min(0.99, weighted + regression))

        done = correctness == 1.0 or step_count >= max_steps

        components: Dict[str, float] = {
            "correctness": correctness,
            "efficiency": efficiency,
            "quality": quality,
            "diagnostic": diagnostic,
            "regression": regression,
            "total": total_reward,
        }

        return total_reward, done, components
