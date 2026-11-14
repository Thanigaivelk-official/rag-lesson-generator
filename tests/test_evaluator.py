"""
tests/test_evaluator.py — Unit tests for the independent quality evaluator.

All tests use the rule-based mock evaluator (no API calls required).
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from evaluator import evaluate_lesson, _contains_retrain_error, _build_mock_evaluation
from generator import MOCK_LESSON
from schemas import EvaluationResult, Status


# ======================================================================= #
#  Fixtures
# ======================================================================= #

@pytest.fixture(autouse=True)
def mock_mode(monkeypatch):
    """Force mock/rule-based evaluator for all tests."""
    import config as cfg
    monkeypatch.setattr(cfg.Config, "effective_mock_mode", classmethod(lambda cls: True))


RETRAIN_ERROR_SNIPPET = """
RAG retrains the LLM every time a new document is uploaded.
This retraining process updates the model weights so the LLM knows the new content.
"""

MISSING_GLOSSARY_CONTENT = """
# Introduction to RAG
RAG is a system that retrieves documents and generates answers.
It uses embeddings and vector databases.
Here is an example: a chatbot searches documents and answers.
Another example: a university uses it for student queries.
Document loading, chunking, vector storage, retrieval, generation are all covered.
"""

MISSING_MCQ_CONTENT = """
# A Lesson Without Assessment Questions
## Glossary
- RAG: Retrieval-Augmented Generation
- Embedding: a list of numbers representing text meaning
- Chunk: a small piece of a document
- Vector database: a database storing embeddings
- Retrieval: finding relevant chunks
- Augmented Prompt: question plus retrieved context
- Inference: when the AI generates an answer
RAG uses document loading, chunking, embeddings, vector databases, retrieval, augmented prompts, and generation.
Example one: a hospital chatbot. Example two: a university library system.
No quiz questions are included in this lesson.
"""


# ======================================================================= #
#  Tests — evaluate_lesson return type
# ======================================================================= #

class TestEvaluationReturnType:
    def test_returns_evaluation_result(self):
        result = evaluate_lesson(MOCK_LESSON, "Introduction to RAG")
        assert isinstance(result, EvaluationResult)

    def test_overall_status_is_pass_or_fail(self):
        result = evaluate_lesson(MOCK_LESSON, "Introduction to RAG")
        assert result.overall_status in (Status.PASS, Status.FAIL)

    def test_criteria_has_seven_entries(self):
        result = evaluate_lesson(MOCK_LESSON, "Introduction to RAG")
        assert len(result.criteria) == 7

    def test_failed_criteria_is_list(self):
        result = evaluate_lesson(MOCK_LESSON, "Introduction to RAG")
        assert isinstance(result.failed_criteria, list)

    def test_regeneration_instructions_is_list(self):
        result = evaluate_lesson(MOCK_LESSON, "Introduction to RAG")
        assert isinstance(result.regeneration_instructions, list)


# ======================================================================= #
#  Tests — PASS decision on good lesson
# ======================================================================= #

class TestPassDecision:
    def test_good_lesson_passes(self):
        """The standard mock lesson should pass all 7 criteria."""
        result = evaluate_lesson(MOCK_LESSON, "Introduction to RAG")
        assert result.overall_status == Status.PASS

    def test_good_lesson_has_no_failed_criteria(self):
        result = evaluate_lesson(MOCK_LESSON, "Introduction to RAG")
        assert len(result.failed_criteria) == 0

    def test_good_lesson_has_no_regen_instructions(self):
        result = evaluate_lesson(MOCK_LESSON, "Introduction to RAG")
        assert len(result.regeneration_instructions) == 0

    def test_all_criteria_pass_on_good_lesson(self):
        result = evaluate_lesson(MOCK_LESSON, "Introduction to RAG")
        for criterion in result.criteria:
            assert criterion.status == Status.PASS, f"{criterion.criterion} should PASS but got FAIL"


# ======================================================================= #
#  Tests — FAIL decision on bad content
# ======================================================================= #

class TestFailDecision:
    def test_retrain_error_causes_fail(self):
        """Lesson claiming RAG retrains the LLM must FAIL."""
        result = evaluate_lesson(RETRAIN_ERROR_SNIPPET, "Introduction to RAG")
        assert result.overall_status == Status.FAIL

    def test_technical_accuracy_fails_on_retrain_error(self):
        """Technical Accuracy criterion must FAIL when retraining error is present."""
        result = evaluate_lesson(RETRAIN_ERROR_SNIPPET, "Introduction to RAG")
        tech_accuracy = next(
            (c for c in result.criteria if c.criterion == "Technical Accuracy"), None
        )
        assert tech_accuracy is not None
        assert tech_accuracy.status == Status.FAIL

    def test_missing_glossary_causes_fail(self):
        """Content without a glossary must FAIL Jargon Explanation."""
        result = evaluate_lesson(MISSING_GLOSSARY_CONTENT, "Introduction to RAG")
        jargon = next(
            (c for c in result.criteria if c.criterion == "Jargon Explanation"), None
        )
        assert jargon is not None
        assert jargon.status == Status.FAIL

    def test_missing_mcq_causes_fail(self):
        """Content without MCQs must FAIL Knowledge Assessment."""
        result = evaluate_lesson(MISSING_MCQ_CONTENT, "Introduction to RAG")
        assessment = next(
            (c for c in result.criteria if c.criterion == "Knowledge Assessment"), None
        )
        assert assessment is not None
        assert assessment.status == Status.FAIL

    def test_overall_fail_when_any_criterion_fails(self):
        """overall_status must be FAIL whenever any single criterion fails."""
        result = evaluate_lesson(RETRAIN_ERROR_SNIPPET, "Introduction to RAG")
        assert result.overall_status == Status.FAIL

    def test_failed_criteria_list_is_non_empty_on_fail(self):
        result = evaluate_lesson(RETRAIN_ERROR_SNIPPET, "Introduction to RAG")
        assert len(result.failed_criteria) > 0

    def test_regen_instructions_provided_on_fail(self):
        result = evaluate_lesson(RETRAIN_ERROR_SNIPPET, "Introduction to RAG")
        assert len(result.regeneration_instructions) > 0


# ======================================================================= #
#  Tests — retrain error detection helper
# ======================================================================= #

class TestRetrainDetection:
    def test_detects_retrains_the_llm(self):
        assert _contains_retrain_error("RAG retrains the LLM every time") is True

    def test_detects_model_is_retrained(self):
        assert _contains_retrain_error("the model is retrained on new documents") is True

    def test_detects_fine_tunes(self):
        assert _contains_retrain_error("RAG fine-tunes the LLM on each upload") is True

    def test_no_false_positive_on_correct_content(self):
        correct = "RAG retrieves documents at inference time and does not retrain the LLM."
        # This should NOT trigger — the word "retrain" appears but in a negated context.
        # Our regex catches "retrains the llm" / "rag retrain" etc.
        # This sentence has "not retrain" which our patterns should not catch.
        result = _contains_retrain_error(correct)
        # The sentence "does not retrain" should not match "retrains the llm"
        assert result is False

    def test_case_insensitive_detection(self):
        assert _contains_retrain_error("RAG RETRAINS THE LLM EVERY UPLOAD") is True
