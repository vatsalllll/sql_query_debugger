"""
Comprehensive pytest tests for the SQL Debugger RL environment.

Covers: rubrics, bug injection, grader, environment, curriculum,
multi-agent coordination, analytics, model validation, and SQL engine.
"""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# 1. Rubrics tests
# ---------------------------------------------------------------------------

from sql_debugger.server.rubrics import (
    CorrectnessRubric,
    RegressionPenalty,
    CompositeRubric,
)


class TestCorrectnessRubric:
    def setup_method(self):
        self.rubric = CorrectnessRubric()

    def test_correctness_exact_match(self):
        """Exact row set match returns 1.0."""
        actual = [(1, "Alice"), (2, "Bob")]
        expected = [(1, "Alice"), (2, "Bob")]
        score = self.rubric.score(actual, expected, execution_error=None)
        assert score == 1.0

    def test_correctness_execution_error(self):
        """Any execution error returns 0.0 regardless of rows."""
        score = self.rubric.score(
            actual_rows=[(1, "Alice")],
            expected_rows=[(1, "Alice")],
            execution_error="syntax error near 'SELCT'",
        )
        assert score == 0.0

    def test_correctness_partial_match(self):
        """Partial row overlap returns a score strictly between 0.1 and 0.9."""
        actual = [(1, "Alice"), (2, "Bob")]
        expected = [(1, "Alice"), (2, "Bob"), (3, "Charlie")]
        score = self.rubric.score(actual, expected, execution_error=None)
        assert 0.1 < score < 0.9

    def test_correctness_order_by_awareness(self):
        """ORDER BY query uses order-sensitive comparison; wrong order != 1.0."""
        actual = [(2, "Bob"), (1, "Alice")]   # swapped
        expected = [(1, "Alice"), (2, "Bob")]
        query = "SELECT id, name FROM users ORDER BY id"
        score = self.rubric.score(actual, expected, execution_error=None, submitted_query=query)
        assert score < 1.0

        # Correct order should return 1.0
        correct_score = self.rubric.score(
            expected, expected, execution_error=None, submitted_query=query
        )
        assert correct_score == 1.0

    def test_regression_penalty_values(self):
        """RegressionPenalty returns -0.1 for regression, +0.05 for improvement, 0.0 for same."""
        penalty = RegressionPenalty()

        assert penalty.score(correctness=0.5, previous_best=0.8) == -0.1   # regression
        assert penalty.score(correctness=0.9, previous_best=0.7) == 0.05   # improvement
        assert penalty.score(correctness=0.7, previous_best=0.7) == 0.0    # same


# ---------------------------------------------------------------------------
# 2. Bug Injection tests
# ---------------------------------------------------------------------------

from sql_debugger.server.bug_injector import inject_bug, inject_multi_bug

_SIMPLE_QUERY = "SELECT name, email FROM users WHERE age > 25;"
_JOIN_QUERY = "SELECT u.name, COUNT(o.id) FROM users u JOIN orders o ON u.id = o.user_id GROUP BY u.name;"


class TestBugInjection:
    def test_inject_bug_changes_query(self):
        """inject_bug must produce a query different from the original."""
        broken, bug = inject_bug(_SIMPLE_QUERY, difficulty="easy", seed=42)
        assert broken.strip() != _SIMPLE_QUERY.strip()
        assert bug is not None
        assert bug.bug_type  # non-empty string

    def test_inject_bug_reproducible(self):
        """Same seed always yields identical broken query."""
        broken1, _ = inject_bug(_SIMPLE_QUERY, difficulty="easy", seed=7)
        broken2, _ = inject_bug(_SIMPLE_QUERY, difficulty="easy", seed=7)
        assert broken1 == broken2

    def test_inject_multi_bug_chains(self):
        """inject_multi_bug injects at least 2 distinct bugs."""
        broken, bugs = inject_multi_bug(_JOIN_QUERY, difficulty="easy", num_bugs=2, seed=99)
        assert broken.strip() != _JOIN_QUERY.strip()
        assert len(bugs) >= 2


# ---------------------------------------------------------------------------
# 3. Grader tests
# ---------------------------------------------------------------------------

from sql_debugger.server.grader import SQLGrader


class TestGrader:
    def setup_method(self):
        self.grader = SQLGrader()

    def test_grader_perfect_score(self):
        """Correct answer on step 1 of 10 should give high reward and done=True."""
        rows = [(1, "Alice"), (2, "Bob")]
        reward, done = self.grader.grade(
            actual_rows=rows,
            expected_rows=rows,
            execution_error=None,
            step_count=1,
            max_steps=10,
            previous_best=0.0,
        )
        assert done is True
        assert reward >= 0.8

    def test_grader_error_score(self):
        """Execution error should yield low reward (correctness=0, efficiency bonus only)."""
        reward, done = self.grader.grade(
            actual_rows=None,
            expected_rows=[(1, "Alice")],
            execution_error="no such table: usr",
            step_count=1,
            max_steps=10,
            previous_best=0.0,
        )
        # Correctness is 0.0 but legacy grader adds efficiency bonus (0.2 * 0.9 = 0.18)
        assert reward < 0.3
        assert done is False  # step 1 of 10, not yet at budget


# ---------------------------------------------------------------------------
# 4. Environment tests
# ---------------------------------------------------------------------------

from sql_debugger.server.environment import SQLDebuggerEnv
from sql_debugger.models import SQLAction


class TestEnvironment:
    def test_static_seeds_backward_compat(self):
        """Seeds 0-8 (static tasks) should achieve reward >= 0.95 when correct query submitted."""
        for seed in range(9):
            env = SQLDebuggerEnv()
            obs = env.reset(seed=seed)
            from sql_debugger.server.tasks import get_task_by_index
            task = get_task_by_index(seed)
            action = SQLAction(query=task.correct_query)
            step_obs = env.step(action)
            assert step_obs.reward >= 0.95, (
                f"seed={seed} task={task.task_id}: reward={step_obs.reward}"
            )
            env.close()

    def test_reward_decomposition_in_metadata(self):
        """step() metadata must contain reward_components with all expected keys."""
        env = SQLDebuggerEnv()
        obs = env.reset(seed=0)
        from sql_debugger.server.tasks import get_task_by_index
        task = get_task_by_index(0)
        action = SQLAction(query=task.correct_query)
        step_obs = env.step(action)
        components = step_obs.metadata.get("reward_components", {})
        for key in ("correctness", "efficiency", "quality", "diagnostic", "regression", "total"):
            assert key in components, f"Missing key '{key}' in reward_components"
        env.close()

    def test_curriculum_in_metadata(self):
        """Both reset() and step() observations must carry curriculum info."""
        env = SQLDebuggerEnv()
        reset_obs = env.reset(seed=0)
        assert "curriculum" in reset_obs.metadata, "curriculum missing from reset obs"
        curriculum = reset_obs.metadata["curriculum"]
        assert "level_name" in curriculum
        assert "current_level" in curriculum

        from sql_debugger.server.tasks import get_task_by_index
        task = get_task_by_index(0)
        step_obs = env.step(SQLAction(query=task.correct_query))
        assert "curriculum" in step_obs.metadata
        env.close()


# ---------------------------------------------------------------------------
# 5. Curriculum tests
# ---------------------------------------------------------------------------

from sql_debugger.server.curriculum import CurriculumManager


class TestCurriculum:
    def test_curriculum_promotion(self):
        """10 high-reward episodes (>= promotion_threshold) should advance the level."""
        mgr = CurriculumManager(
            promotion_threshold=0.85,
            demotion_threshold=0.4,
            min_episodes_for_promotion=10,
            min_episodes_for_demotion=5,
        )
        initial_level = mgr.get_info()["current_level"]
        for _ in range(10):
            mgr.record_episode("easy", reward=1.0)
        assert mgr.get_info()["current_level"] == initial_level + 1

    def test_curriculum_demotion(self):
        """5 low-reward episodes (<= demotion_threshold) should decrease the level."""
        mgr = CurriculumManager(
            promotion_threshold=0.85,
            demotion_threshold=0.4,
            min_episodes_for_promotion=10,
            min_episodes_for_demotion=5,
        )
        # Promote first so demotion has room to go down
        for _ in range(10):
            mgr.record_episode("easy", reward=1.0)
        promoted_level = mgr.get_info()["current_level"]
        assert promoted_level > 0

        # Now demote
        for _ in range(5):
            mgr.record_episode("easy", reward=0.1)
        assert mgr.get_info()["current_level"] < promoted_level


# ---------------------------------------------------------------------------
# 6. Multi-Agent tests
# ---------------------------------------------------------------------------

from sql_debugger.server.multi_agent import SessionCoordinator


class TestMultiAgent:
    def test_competitive_first_solver_bonus(self):
        """First solver in a competitive group receives a positive bonus."""
        coord = SessionCoordinator()
        coord.register_session("agent_a", group_id="g1", mode="competitive", seed=42)
        coord.register_session("agent_b", group_id="g1", mode="competitive", seed=42)

        # agent_a solves first
        coord.record_step("agent_a", reward=0.9, query="SELECT 1", correctness=1.0)

        bonus = coord.compute_multi_agent_bonus("agent_a", base_reward=0.9)
        assert bonus > 0.0, f"Expected positive bonus for first solver, got {bonus}"

    def test_single_agent_no_multi_agent_metadata(self):
        """Without group_id, reset() metadata must NOT contain 'multi_agent'."""
        env = SQLDebuggerEnv()
        obs = env.reset(seed=0)
        assert "multi_agent" not in obs.metadata, (
            "multi_agent should not appear in metadata for single-agent mode"
        )
        env.close()


# ---------------------------------------------------------------------------
# 7. Analytics tests
# ---------------------------------------------------------------------------

from sql_debugger.server.analytics import AnalyticsCollector


class TestAnalytics:
    def test_analytics_summary(self):
        """After recording 3 episodes the summary should reflect correct counts and rates."""
        collector = AnalyticsCollector()

        episodes = [
            ("ep1", "task_1", "easy", "keyword_typo", 1.0, True),
            ("ep2", "task_2", "medium", "wrong_column", 0.5, False),
            ("ep3", "task_3", "easy", "keyword_typo", 1.0, True),
        ]

        for ep_id, task_id, diff, bug_type, final_reward, fixed in episodes:
            collector.start_episode(ep_id, task_id, diff, bug_type)
            correctness = 1.0 if fixed else 0.5
            collector.record_step(ep_id, reward=final_reward, correctness=correctness, query="SELECT 1")
            collector.finish_episode(ep_id)

        summary = collector.get_summary()

        assert summary["total_episodes"] == 3
        assert abs(summary["avg_reward"] - (1.0 + 0.5 + 1.0) / 3) < 1e-6
        assert abs(summary["success_rate"] - 2 / 3) < 1e-6
        assert "easy" in summary["avg_reward_by_difficulty"]
        assert "medium" in summary["avg_reward_by_difficulty"]
        assert "keyword_typo" in summary["success_rate_by_bug_type"]


# ---------------------------------------------------------------------------
# 8. Model Validation tests
# ---------------------------------------------------------------------------


class TestModelValidation:
    def test_empty_query_rejected(self):
        """SQLAction with empty or whitespace-only query must raise ValueError."""
        with pytest.raises((ValueError, Exception)):
            SQLAction(query="")

        with pytest.raises((ValueError, Exception)):
            SQLAction(query="   ")


# ---------------------------------------------------------------------------
# 9. SQL Engine tests
# ---------------------------------------------------------------------------

from sql_debugger.server.sql_engine import SQLiteEngine


class TestSQLEngine:
    def test_error_categorization(self):
        """categorize_error must map error strings to the correct category labels."""
        cases = [
            ("no such table: users", "missing_table"),
            ("no such column: username", "missing_column"),
            ("ambiguous column name: id", "ambiguous_column"),
            ("near 'SELCT': syntax error", "syntax"),
            ("query execution timed out (exceeded 5 seconds)", "timeout"),
        ]
        for error_msg, expected_category in cases:
            result = SQLiteEngine.categorize_error(error_msg)
            assert result == expected_category, (
                f"Error '{error_msg}' → expected '{expected_category}', got '{result}'"
            )
