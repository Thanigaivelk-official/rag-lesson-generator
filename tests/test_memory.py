"""
tests/test_memory.py — Unit tests for the persistent memory module.
"""

import sys
import uuid
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import database as db
import memory as mem
from config import config


# ======================================================================= #
#  Fixtures
# ======================================================================= #

@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """Use an isolated SQLite database for each test."""
    test_db = str(tmp_path / "memory_test.db")
    monkeypatch.setattr(config, "DATABASE_PATH", test_db)
    monkeypatch.setattr("database.config.DATABASE_PATH", test_db)
    db.init_db()
    yield


# ======================================================================= #
#  Tests — failure pattern recording
# ======================================================================= #

class TestFailurePatternRecording:
    def test_records_single_failure(self):
        mem.record_evaluation_failures(
            criteria_results=[
                {"criterion": "Technical Accuracy", "status": "FAIL", "reason": "Error found", "suggestion": "Fix it"}
            ],
            topic="Introduction to RAG",
        )
        patterns = db.get_memory_patterns(min_failures=1)
        assert len(patterns) == 1
        assert patterns[0]["criterion"] == "Technical Accuracy"
        assert patterns[0]["failure_count"] == 1

    def test_increments_failure_count_on_repeat(self):
        for _ in range(3):
            mem.record_evaluation_failures(
                criteria_results=[
                    {"criterion": "Beginner-Friendly Language", "status": "FAIL",
                     "reason": "Too complex", "suggestion": "Simplify"}
                ],
                topic="Introduction to RAG",
            )
        patterns = db.get_memory_patterns(min_failures=1)
        assert patterns[0]["failure_count"] == 3

    def test_ignores_passing_criteria(self):
        mem.record_evaluation_failures(
            criteria_results=[
                {"criterion": "Technical Accuracy", "status": "PASS", "reason": "OK", "suggestion": ""}
            ],
            topic="Introduction to RAG",
        )
        patterns = db.get_memory_patterns(min_failures=1)
        assert len(patterns) == 0

    def test_records_multiple_different_criteria(self):
        mem.record_evaluation_failures(
            criteria_results=[
                {"criterion": "Technical Accuracy", "status": "FAIL", "reason": "Error", "suggestion": "Fix"},
                {"criterion": "Practical Examples", "status": "FAIL", "reason": "Missing", "suggestion": "Add"},
                {"criterion": "Jargon Explanation", "status": "PASS", "reason": "OK", "suggestion": ""},
            ],
            topic="Introduction to RAG",
        )
        patterns = db.get_memory_patterns(min_failures=1)
        criterion_names = [p["criterion"] for p in patterns]
        assert "Technical Accuracy" in criterion_names
        assert "Practical Examples" in criterion_names
        assert "Jargon Explanation" not in criterion_names


# ======================================================================= #
#  Tests — improvement hints
# ======================================================================= #

class TestImprovementHints:
    def test_no_hints_below_threshold(self):
        """No hints should be returned when failure count is below threshold."""
        mem.record_evaluation_failures(
            criteria_results=[
                {"criterion": "Technical Accuracy", "status": "FAIL", "reason": "Error", "suggestion": "Fix"}
            ],
            topic="Intro to RAG",
        )
        # Only 1 failure — below threshold of 2
        hint = mem.get_improvement_hints()
        assert hint is None

    def test_hints_returned_above_threshold(self):
        """Hints should be returned when failure count meets threshold."""
        for _ in range(mem.FAILURE_THRESHOLD):
            mem.record_evaluation_failures(
                criteria_results=[
                    {"criterion": "Practical Examples", "status": "FAIL",
                     "reason": "No examples", "suggestion": "Add examples"}
                ],
                topic="Intro to RAG",
            )
        hint = mem.get_improvement_hints()
        assert hint is not None
        assert "Practical Examples" in hint


# ======================================================================= #
#  Tests — self-improvement generation
# ======================================================================= #

class TestSelfImprovement:
    def test_generates_improvement_above_threshold(self):
        """An improvement instruction should be saved when threshold is met."""
        for _ in range(mem.FAILURE_THRESHOLD):
            mem.record_evaluation_failures(
                criteria_results=[
                    {"criterion": "Jargon Explanation", "status": "FAIL",
                     "reason": "No glossary", "suggestion": "Add glossary"}
                ],
                topic="Intro to RAG",
            )
        new = mem.generate_and_save_improvements()
        assert len(new) > 0

    def test_does_not_duplicate_improvements(self):
        """Calling generate_and_save twice should not duplicate entries."""
        for _ in range(mem.FAILURE_THRESHOLD):
            mem.record_evaluation_failures(
                criteria_results=[
                    {"criterion": "Beginner-Friendly Language", "status": "FAIL",
                     "reason": "Too complex", "suggestion": "Simplify"}
                ],
                topic="Intro to RAG",
            )
        first_call = mem.generate_and_save_improvements()
        second_call = mem.generate_and_save_improvements()
        # Second call should return empty (already saved)
        assert len(second_call) == 0

    def test_improvement_stored_in_database(self):
        """Generated improvement should appear in the prompt_improvements table."""
        for _ in range(mem.FAILURE_THRESHOLD):
            mem.record_evaluation_failures(
                criteria_results=[
                    {"criterion": "Knowledge Assessment", "status": "FAIL",
                     "reason": "No MCQs", "suggestion": "Add MCQs"}
                ],
                topic="Intro to RAG",
            )
        mem.generate_and_save_improvements()
        improvements = db.get_prompt_improvements()
        assert any(imp["criterion"] == "Knowledge Assessment" for imp in improvements)


# ======================================================================= #
#  Tests — persistence across restarts
# ======================================================================= #

class TestPersistence:
    def test_patterns_persist_across_connections(self, tmp_path, monkeypatch):
        """Patterns written in one connection should be readable in another."""
        test_db = str(tmp_path / "persist_test.db")
        monkeypatch.setattr(config, "DATABASE_PATH", test_db)
        monkeypatch.setattr("database.config.DATABASE_PATH", test_db)
        db.init_db()

        # Write
        db.upsert_memory_pattern("Technical Accuracy", "Error detected", "Fix it")

        # Simulate re-connection (get_connection creates a new connection each time)
        patterns = db.get_memory_patterns(min_failures=1)
        assert len(patterns) == 1
        assert patterns[0]["criterion"] == "Technical Accuracy"

    def test_runs_persist_in_database(self, tmp_path, monkeypatch):
        """Run records should persist across connections."""
        test_db = str(tmp_path / "run_persist_test.db")
        monkeypatch.setattr(config, "DATABASE_PATH", test_db)
        monkeypatch.setattr("database.config.DATABASE_PATH", test_db)
        db.init_db()

        run_id = str(uuid.uuid4())[:8].upper()
        db.create_run(run_id=run_id, topic="Test Topic")
        db.update_run_status(run_id, "APPROVED", retry_count=0)

        retrieved = db.get_run(run_id)
        assert retrieved is not None
        assert retrieved["final_status"] == "APPROVED"
