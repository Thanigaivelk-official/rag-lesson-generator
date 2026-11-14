"""
tests/test_generator.py — Unit tests for the content generator.

All tests use mocked LLM responses so no API credits are consumed.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas import GenerationRequest, GeneratedLesson, LearnerLevel
from generator import generate_lesson, MOCK_LESSON


# ======================================================================= #
#  Fixtures
# ======================================================================= #

@pytest.fixture(autouse=True)
def mock_mode(monkeypatch):
    """Force mock mode for all tests in this module."""
    monkeypatch.setattr("config.config.MOCK_MODE", True)
    monkeypatch.setattr("config.Config.MOCK_MODE", True)
    # Patch effective_mock_mode to always return True
    import config as cfg
    monkeypatch.setattr(cfg.Config, "effective_mock_mode", classmethod(lambda cls: True))


# ======================================================================= #
#  Tests
# ======================================================================= #

class TestGenerateLesson:
    """Tests for the generate_lesson function."""

    def test_returns_generated_lesson_instance(self):
        """generate_lesson should return a GeneratedLesson object."""
        request = GenerationRequest(topic="Introduction to RAG", attempt_number=1)
        result = generate_lesson(request)
        assert isinstance(result, GeneratedLesson)

    def test_title_is_non_empty(self):
        """Generated lesson must have a non-empty title."""
        request = GenerationRequest(topic="Introduction to RAG", attempt_number=1)
        result = generate_lesson(request)
        assert result.title.strip() != ""

    def test_content_is_non_empty(self):
        """Generated lesson must have non-empty content."""
        request = GenerationRequest(topic="Introduction to RAG", attempt_number=1)
        result = generate_lesson(request)
        assert len(result.content.strip()) > 100

    def test_topic_is_preserved(self):
        """Topic in result should match the requested topic."""
        topic = "Introduction to RAG"
        request = GenerationRequest(topic=topic, attempt_number=1)
        result = generate_lesson(request)
        assert result.topic == topic

    def test_attempt_number_preserved(self):
        """Attempt number in result should match the request."""
        request = GenerationRequest(topic="Introduction to RAG", attempt_number=2)
        result = generate_lesson(request)
        assert result.attempt_number == 2

    def test_word_count_is_positive(self):
        """Word count should be greater than zero."""
        request = GenerationRequest(topic="Introduction to RAG", attempt_number=1)
        result = generate_lesson(request)
        assert result.word_count > 0

    def test_learner_level_default_is_beginner(self):
        """Default learner level should be Beginner."""
        request = GenerationRequest(topic="Introduction to RAG", attempt_number=1)
        result = generate_lesson(request)
        assert result.learner_level == LearnerLevel.BEGINNER

    def test_accepts_previous_feedback(self):
        """Generator should accept previous_feedback without error."""
        request = GenerationRequest(
            topic="Introduction to RAG",
            attempt_number=2,
            previous_feedback="Please add more examples.",
        )
        result = generate_lesson(request)
        assert isinstance(result, GeneratedLesson)

    def test_accepts_improvement_hints(self):
        """Generator should accept improvement_hints without error."""
        request = GenerationRequest(
            topic="Introduction to RAG",
            attempt_number=1,
            improvement_hints="Focus on simple language.",
        )
        result = generate_lesson(request)
        assert isinstance(result, GeneratedLesson)

    def test_mock_lesson_contains_rag_content(self):
        """Mock lesson must contain RAG-related content."""
        request = GenerationRequest(topic="Introduction to RAG", attempt_number=1)
        result = generate_lesson(request)
        content_lower = result.content.lower()
        assert "rag" in content_lower
        assert "retrieval" in content_lower

    def test_mock_lesson_contains_glossary(self):
        """Mock lesson should contain a glossary section."""
        request = GenerationRequest(topic="Introduction to RAG", attempt_number=1)
        result = generate_lesson(request)
        assert "glossary" in result.content.lower()

    def test_mock_lesson_contains_mcq(self):
        """Mock lesson should contain multiple-choice questions."""
        request = GenerationRequest(topic="Introduction to RAG", attempt_number=1)
        result = generate_lesson(request)
        content_lower = result.content.lower()
        assert "question 1" in content_lower or "mcq" in content_lower or "multiple choice" in content_lower
