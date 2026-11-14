"""
tests/test_stress_test.py — Automated tests for the deliberate error stress test.

Verifies that:
1. A lesson containing "RAG retrains the LLM" causes Technical Accuracy to FAIL.
2. The agent catches the error and triggers a retry.
3. The corrected lesson (without the error) passes Technical Accuracy.
4. The full workflow terminates correctly.

No API credits required — uses the rule-based mock evaluator.
"""

import sys
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import database as db
from agent import run_agent
from config import config
from evaluator import evaluate_lesson, _contains_retrain_error
from generator import MOCK_LESSON
from prompts import STRESS_TEST_INJECTION
from schemas import EvaluationResult, Status, RunStatus


# ======================================================================= #
#  Fixtures
# ======================================================================= #

@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    test_db = str(tmp_path / "stress_test.db")
    monkeypatch.setattr(config, "DATABASE_PATH", test_db)
    monkeypatch.setattr("database.config.DATABASE_PATH", test_db)
    db.init_db()
    yield


@pytest.fixture(autouse=True)
def mock_mode_on(monkeypatch):
    import config as cfg
    monkeypatch.setattr(cfg.Config, "effective_mock_mode", classmethod(lambda cls: True))


FAULTY_LESSON = MOCK_LESSON + "\n\n" + STRESS_TEST_INJECTION


# ======================================================================= #
#  Tests — error detection
# ======================================================================= #

class TestErrorDetection:
    def test_retrain_error_detected_in_faulty_lesson(self):
        """The faulty lesson must be detected as containing retraining misinformation."""
        assert _contains_retrain_error(FAULTY_LESSON) is True

    def test_no_retrain_error_in_clean_lesson(self):
        """The standard mock lesson must NOT trigger the retraining detection."""
        assert _contains_retrain_error(MOCK_LESSON) is False

    def test_evaluator_marks_technical_accuracy_fail(self):
        """Evaluator must mark Technical Accuracy as FAIL on the faulty lesson."""
        result = evaluate_lesson(FAULTY_LESSON, "Introduction to RAG")
        tech = next((c for c in result.criteria if c.criterion == "Technical Accuracy"), None)
        assert tech is not None, "Technical Accuracy criterion must be present"
        assert tech.status == Status.FAIL, "Technical Accuracy must FAIL on faulty lesson"

    def test_evaluator_overall_fail_on_faulty_lesson(self):
        """Overall evaluation must be FAIL when Technical Accuracy fails."""
        result = evaluate_lesson(FAULTY_LESSON, "Introduction to RAG")
        assert result.overall_status == Status.FAIL

    def test_evaluator_includes_correction_suggestion(self):
        """Evaluator must provide a correction suggestion for the retraining error."""
        result = evaluate_lesson(FAULTY_LESSON, "Introduction to RAG")
        tech = next((c for c in result.criteria if c.criterion == "Technical Accuracy"), None)
        assert tech is not None
        assert tech.suggestion.strip() != "", "Suggestion must not be empty for a FAIL"

    def test_clean_lesson_passes_technical_accuracy(self):
        """The standard mock lesson must PASS Technical Accuracy."""
        result = evaluate_lesson(MOCK_LESSON, "Introduction to RAG")
        tech = next((c for c in result.criteria if c.criterion == "Technical Accuracy"), None)
        assert tech is not None
        assert tech.status == Status.PASS


# ======================================================================= #
#  Tests — full stress-test workflow
# ======================================================================= #

class TestStressTestWorkflow:
    def test_stress_test_triggers_retry(self):
        """When a faulty lesson is injected, the agent must retry at least once."""
        run_id = str(uuid.uuid4())[:8].upper()
        state = run_agent(
            topic="Introduction to RAG",
            run_id=run_id,
            stress_test_content=FAULTY_LESSON,
        )
        # retry_count > 0 means at least one retry happened
        assert state["retry_count"] >= 1, "Agent should have retried after the faulty lesson failed"

    def test_stress_test_first_evaluation_fails(self):
        """The first evaluation result in history must be FAIL."""
        run_id = str(uuid.uuid4())[:8].upper()
        state = run_agent(
            topic="Introduction to RAG",
            run_id=run_id,
            stress_test_content=FAULTY_LESSON,
        )
        eval_history = state.get("evaluation_history", [])
        assert len(eval_history) >= 1
        first_eval = eval_history[0]
        first_status = first_eval.get("overall_status") if isinstance(first_eval, dict) else first_eval.overall_status
        assert first_status == Status.FAIL.value or first_status == Status.FAIL

    def test_stress_test_rejection_logged(self):
        """A rejection log entry should be created for the failed first attempt."""
        run_id = str(uuid.uuid4())[:8].upper()
        run_agent(
            topic="Introduction to RAG",
            run_id=run_id,
            stress_test_content=FAULTY_LESSON,
        )
        rejections = db.get_rejections_for_run(run_id)
        assert len(rejections) >= 1

    def test_stress_test_technical_accuracy_in_rejection(self):
        """The rejection log should mention Technical Accuracy as a failed criterion."""
        run_id = str(uuid.uuid4())[:8].upper()
        run_agent(
            topic="Introduction to RAG",
            run_id=run_id,
            stress_test_content=FAULTY_LESSON,
        )
        rejections = db.get_rejections_for_run(run_id)
        first_rejection = rejections[0]
        assert "Technical Accuracy" in first_rejection["failed_criteria"]

    def test_stress_test_corrected_lesson_passes(self):
        """After correction (second attempt uses clean mock lesson), the lesson should pass."""
        run_id = str(uuid.uuid4())[:8].upper()
        state = run_agent(
            topic="Introduction to RAG",
            run_id=run_id,
            stress_test_content=FAULTY_LESSON,
        )
        # The corrected second attempt (from generate_lesson using MOCK_LESSON) should pass
        final_status = state.get("final_status")
        assert final_status == RunStatus.APPROVED.value, (
            f"After stress-test correction, lesson should be APPROVED, got {final_status}"
        )

    def test_stress_test_generates_feedback_for_correction(self):
        """The agent should provide feedback about the Technical Accuracy failure."""
        run_id = str(uuid.uuid4())[:8].upper()
        state = run_agent(
            topic="Introduction to RAG",
            run_id=run_id,
            stress_test_content=FAULTY_LESSON,
        )
        # Verify evaluation history shows the progression
        eval_history = state.get("evaluation_history", [])
        assert len(eval_history) >= 2, "Should have at least 2 evaluation records (faulty + corrected)"

    def test_maximum_retry_not_exceeded_in_stress_test(self):
        """Even in stress test mode, retries must not exceed MAX_RETRIES."""
        run_id = str(uuid.uuid4())[:8].upper()
        state = run_agent(
            topic="Introduction to RAG",
            run_id=run_id,
            stress_test_content=FAULTY_LESSON,
        )
        assert state["retry_count"] <= config.MAX_RETRIES
