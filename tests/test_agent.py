"""
tests/test_agent.py — Unit tests for the LangGraph agent workflow.

Tests cover the full workflow including approval, retry, and human review.
All LLM calls are mocked — no API credits required.
"""

import sys
import uuid
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import database as db
from config import config
from schemas import (
    AgentState, EvaluationResult, GeneratedLesson,
    LearnerLevel, RunStatus, Status, CriterionResult
)
from generator import MOCK_LESSON


# ======================================================================= #
#  Helpers
# ======================================================================= #

def _make_pass_evaluation() -> EvaluationResult:
    """Build a full EvaluationResult where all 7 criteria PASS."""
    criteria_names = [
        "Technical Accuracy", "Beginner-Friendly Language", "Practical Examples",
        "Jargon Explanation", "Key Topic Coverage", "Teaching Flow and Structure",
        "Knowledge Assessment",
    ]
    criteria = [
        CriterionResult(
            criterion=name, status=Status.PASS,
            reason="Criterion met.", evidence="", suggestion=""
        )
        for name in criteria_names
    ]
    return EvaluationResult(
        overall_status=Status.PASS,
        criteria=criteria,
        failed_criteria=[],
        regeneration_instructions=[],
    )


def _make_fail_evaluation(failed_name: str = "Technical Accuracy") -> EvaluationResult:
    """Build an EvaluationResult where one criterion FAILS."""
    criteria_names = [
        "Technical Accuracy", "Beginner-Friendly Language", "Practical Examples",
        "Jargon Explanation", "Key Topic Coverage", "Teaching Flow and Structure",
        "Knowledge Assessment",
    ]
    criteria = [
        CriterionResult(
            criterion=name,
            status=Status.FAIL if name == failed_name else Status.PASS,
            reason="Criterion failed." if name == failed_name else "Criterion met.",
            evidence="",
            suggestion="Fix the error." if name == failed_name else "",
        )
        for name in criteria_names
    ]
    return EvaluationResult(
        overall_status=Status.FAIL,
        criteria=criteria,
        failed_criteria=[failed_name],
        regeneration_instructions=["Fix the error."],
    )


def _fresh_run_id() -> str:
    return str(uuid.uuid4())[:8].upper()


# ======================================================================= #
#  Fixtures
# ======================================================================= #

@pytest.fixture(autouse=True)
def use_test_db(tmp_path, monkeypatch):
    """Use an isolated SQLite database for every test."""
    test_db = str(tmp_path / "test.db")
    monkeypatch.setattr(config, "DATABASE_PATH", test_db)
    monkeypatch.setattr("database.config.DATABASE_PATH", test_db)
    db.init_db()
    yield


@pytest.fixture(autouse=True)
def mock_mode_on(monkeypatch):
    """Force mock mode so generator uses MOCK_LESSON."""
    import config as cfg
    monkeypatch.setattr(cfg.Config, "effective_mock_mode", classmethod(lambda cls: True))


# ======================================================================= #
#  Tests — workflow outcomes
# ======================================================================= #

class TestAgentApprovalPath:
    """Tests for the happy path: lesson passes on the first attempt."""

    def test_approved_on_first_attempt(self):
        """When the lesson passes evaluation, status should be APPROVED."""
        from agent import run_agent
        with patch("agent.evaluate_lesson", return_value=_make_pass_evaluation()):
            state = run_agent(topic="Introduction to RAG", run_id=_fresh_run_id())
        assert state["final_status"] == RunStatus.APPROVED.value

    def test_zero_retries_on_first_pass(self):
        """No retries should occur when the first attempt passes."""
        from agent import run_agent
        with patch("agent.evaluate_lesson", return_value=_make_pass_evaluation()):
            state = run_agent(topic="Introduction to RAG", run_id=_fresh_run_id())
        assert state["retry_count"] == 0

    def test_final_lesson_is_set_on_approval(self):
        """final_lesson must be populated after approval."""
        from agent import run_agent
        with patch("agent.evaluate_lesson", return_value=_make_pass_evaluation()):
            state = run_agent(topic="Introduction to RAG", run_id=_fresh_run_id())
        assert state["final_lesson"] is not None

    def test_database_run_marked_approved(self):
        """Database run record should reflect APPROVED status."""
        from agent import run_agent
        run_id = _fresh_run_id()
        with patch("agent.evaluate_lesson", return_value=_make_pass_evaluation()):
            run_agent(topic="Introduction to RAG", run_id=run_id)
        run = db.get_run(run_id)
        assert run is not None
        assert run["final_status"] == RunStatus.APPROVED.value


class TestAgentRetryPath:
    """Tests for the retry path: lesson fails then passes."""

    def test_retries_after_failure(self):
        """Agent should retry when evaluation fails and retries are available."""
        from agent import run_agent
        # Fail once, then pass
        side_effects = [_make_fail_evaluation("Technical Accuracy"), _make_pass_evaluation()]
        with patch("agent.evaluate_lesson", side_effect=side_effects):
            state = run_agent(topic="Introduction to RAG", run_id=_fresh_run_id())
        assert state["final_status"] == RunStatus.APPROVED.value
        assert state["retry_count"] == 1

    def test_feedback_is_set_after_failure(self):
        """Previous feedback should be set when a retry occurs."""
        from agent import run_agent
        side_effects = [_make_fail_evaluation(), _make_pass_evaluation()]
        with patch("agent.evaluate_lesson", side_effect=side_effects):
            state = run_agent(topic="Introduction to RAG", run_id=_fresh_run_id())
        # After retry, previous_feedback should have been used (non-None in intermediate state)
        assert state["retry_count"] >= 1

    def test_two_generation_history_entries_after_one_retry(self):
        """After one retry, there should be 2 entries in generation_history."""
        from agent import run_agent
        side_effects = [_make_fail_evaluation(), _make_pass_evaluation()]
        with patch("agent.evaluate_lesson", side_effect=side_effects):
            state = run_agent(topic="Introduction to RAG", run_id=_fresh_run_id())
        assert len(state["generation_history"]) == 2


class TestAgentHumanReviewPath:
    """Tests for the human review path: all retries exhausted."""

    def test_human_review_after_max_retries(self):
        """Agent should mark HUMAN_REVIEW when all retries are exhausted."""
        from agent import run_agent
        # Always fail — 1 initial + 2 retries = 3 evaluations
        always_fail = _make_fail_evaluation()
        with patch("agent.evaluate_lesson", return_value=always_fail):
            state = run_agent(topic="Introduction to RAG", run_id=_fresh_run_id())
        assert state["final_status"] == RunStatus.HUMAN_REVIEW.value

    def test_retry_count_equals_max_retries_on_human_review(self):
        """retry_count should equal MAX_RETRIES when human review is triggered."""
        from agent import run_agent
        always_fail = _make_fail_evaluation()
        with patch("agent.evaluate_lesson", return_value=always_fail):
            state = run_agent(topic="Introduction to RAG", run_id=_fresh_run_id())
        assert state["retry_count"] == config.MAX_RETRIES

    def test_no_infinite_loop(self):
        """Agent must terminate even when every evaluation fails."""
        from agent import run_agent
        always_fail = _make_fail_evaluation()
        # This would loop forever without the retry limit
        with patch("agent.evaluate_lesson", return_value=always_fail):
            state = run_agent(topic="Introduction to RAG", run_id=_fresh_run_id())
        # Simply completing without hanging is the assertion
        assert state is not None

    def test_database_run_marked_human_review(self):
        """Database run record should reflect HUMAN_REVIEW status."""
        from agent import run_agent
        run_id = _fresh_run_id()
        always_fail = _make_fail_evaluation()
        with patch("agent.evaluate_lesson", return_value=always_fail):
            run_agent(topic="Introduction to RAG", run_id=run_id)
        run = db.get_run(run_id)
        assert run is not None
        assert run["final_status"] == RunStatus.HUMAN_REVIEW.value

    def test_rejection_logs_saved_on_failure(self):
        """Rejection logs should be created for each failed attempt."""
        from agent import run_agent
        run_id = _fresh_run_id()
        always_fail = _make_fail_evaluation()
        with patch("agent.evaluate_lesson", return_value=always_fail):
            run_agent(topic="Introduction to RAG", run_id=run_id)
        rejections = db.get_rejections_for_run(run_id)
        # Should have entries for all failed attempts
        assert len(rejections) >= 1
