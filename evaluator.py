"""
evaluator.py — Independent AI quality evaluator module.

Evaluates a generated lesson against the seven-criterion rubric.
Completely independent of the generator — it has no access to generator
prompts or logic. Decisions are based solely on lesson content.

Supports both real OpenAI calls and a mock mode for testing.
"""

import json
import logging
import re
from typing import Any, Dict

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from config import config
from rubric import CRITERION_NAMES
from schemas import CriterionResult, EvaluationResult, Status
from prompts import EVALUATOR_SYSTEM_PROMPT, build_evaluator_user_prompt

logger = logging.getLogger(__name__)


# ======================================================================= #
#  Deterministic rule-based checks (used in mock mode and as safety net)
# ======================================================================= #

# Phrases that indicate a known technical error about RAG retraining.
# We detect ASSERTIVE claims that RAG retrains, while ignoring correct negations like
# "RAG does NOT retrain", "thinking RAG retrains: it does not", "no need to retrain".
_RETRAIN_ERROR_PATTERNS = [
    # Positively asserts RAG retrains/fine-tunes the LLM
    r"rag\s+retrains\s+the\s+llm",
    r"rag\s+fine.?tun(?:es|ing)\s+the\s+(?:llm|model)",
    r"(?:the\s+)?llm\s+is\s+retrained\s+(?:every|each|when|on)",
    r"retraining\s+(?:the\s+)?llm\s+(?:every|each|when)",
    r"updates\s+(?:the\s+)?model\s+weights\s+(?:so|when|every|each)",
    r"fine.?tun.*every\s+time\s+a\s+new\s+document\s+is\s+(?:upload|add)",
    r"model\s+is\s+retrained\s+on\s+(?:each|every|new)",
    r"new\s+document.*retrain.*llm",
]

# Negation words that indicate the sentence is CORRECTING the misconception
_NEGATION_WINDOW = 60  # chars before/after match to check for negation


def _contains_retrain_error(content: str) -> bool:
    """
    Return True if the lesson content contains assertive retraining misinformation.

    Avoids false positives from correct statements like:
    - "Thinking RAG retrains the LLM: it does NOT."
    - "No need to retrain the expensive LLM."
    - "RAG does NOT retrain the model."
    """
    lower = content.lower()
    negation_words = ["not ", "does not", "do not", "doesn't", "don't",
                      "never", "no need", "without retraining", "thinking rag",
                      "misconception", "incorrect", "wrong", "myth"]

    for pat in _RETRAIN_ERROR_PATTERNS:
        for m in re.finditer(pat, lower):
            # Check surrounding context for negation
            start = max(0, m.start() - _NEGATION_WINDOW)
            end = min(len(lower), m.end() + _NEGATION_WINDOW)
            context = lower[start:end]
            if not any(neg in context for neg in negation_words):
                return True
    return False


def _has_glossary(content: str) -> bool:
    """Return True only if a GLOSSARY SECTION exists (heading, not just a mention)."""
    lower = content.lower()
    # Must have a glossary heading (## glossary, **glossary**, glossary\n, etc.)
    # Exclude the title of a section called "without a glossary"
    return bool(re.search(r'(?:^|\n)\s*(?:#{1,4}\s*glossary|glossary\s*\n)', lower))


def _has_mcq(content: str) -> bool:
    """Return True if 5 properly formatted MCQs are present."""
    lower = content.lower()
    # Must have at least 5 questions with 4 options AND correct answers
    correct_count = lower.count("✓ correct:") + lower.count("correct answer:") + lower.count("correct: ")
    has_five_questions = (
        (lower.count("question 1") >= 1 and lower.count("question 5") >= 1) or
        correct_count >= 5
    )
    has_options = lower.count(") ") >= 10 or ("a)" in lower and "b)" in lower)
    return has_five_questions and has_options


def _has_practical_examples(content: str) -> bool:
    lower = content.lower()
    example_keywords = ["example", "real-world", "practical", "library", "hospital", "university", "chatbot"]
    return sum(1 for kw in example_keywords if kw in lower) >= 2


def _has_pipeline_coverage(content: str) -> bool:
    lower = content.lower()
    required = ["chunk", "embed", "vector", "retriev", "generat", "document"]
    return all(term in lower for term in required)


def _build_mock_evaluation(content: str) -> EvaluationResult:
    """
    Rule-based evaluation used when MOCK_MODE is active.
    Applies deterministic checks to produce a realistic evaluation.
    """
    criteria_results = []
    failed: list[str] = []
    regen_instructions: list[str] = []

    def _add(criterion: str, pass_cond: bool, reason_pass: str, reason_fail: str, suggestion: str = ""):
        status = Status.PASS if pass_cond else Status.FAIL
        criteria_results.append(CriterionResult(
            criterion=criterion,
            status=status,
            reason=reason_pass if pass_cond else reason_fail,
            evidence="(rule-based check in mock mode)",
            suggestion="" if pass_cond else suggestion,
        ))
        if not pass_cond:
            failed.append(criterion)
            regen_instructions.append(suggestion)

    _add(
        "Technical Accuracy",
        not _contains_retrain_error(content),
        "No retraining errors detected. RAG pipeline described correctly.",
        "Lesson contains a technical error: it states that RAG retrains the LLM. This is incorrect.",
        "Remove the claim that RAG retrains the LLM. Explain that RAG retrieves documents at inference time and does not modify model weights.",
    )
    _add(
        "Beginner-Friendly Language",
        True,
        "Language appears accessible and simple.",
        "Advanced jargon detected without explanation.",
        "Replace technical terms with plain English. Explain each term immediately.",
    )
    _add(
        "Practical Examples",
        _has_practical_examples(content),
        "At least two practical real-world examples are present.",
        "Insufficient practical examples found.",
        "Add at least two clear real-world examples (e.g., university chatbot, hospital records system).",
    )
    _add(
        "Jargon Explanation",
        _has_glossary(content),
        "Glossary section is present.",
        "No glossary section detected.",
        "Add a glossary section defining: RAG, LLM, embedding, chunk, vector database, retrieval, augmented prompt, inference.",
    )
    _add(
        "Key Topic Coverage",
        _has_pipeline_coverage(content),
        "All RAG pipeline steps are covered.",
        "One or more critical pipeline steps (chunk, embed, vector, retrieval, generation) are missing.",
        "Explicitly cover each step: document loading, chunking, embedding, vector storage, retrieval, prompt augmentation, generation.",
    )
    _add(
        "Teaching Flow and Structure",
        True,
        "Content follows a logical, well-structured sequence.",
        "Lesson structure is disorganised.",
        "Reorganise content from basics to advanced. Add clear headings and an introduction/conclusion.",
    )
    _add(
        "Knowledge Assessment",
        _has_mcq(content),
        "Five MCQs with options and answers are present.",
        "MCQ section is missing or incomplete.",
        "Add exactly 5 multiple-choice questions, each with 4 options, a marked correct answer, and a brief explanation.",
    )

    overall = Status.PASS if not failed else Status.FAIL
    return EvaluationResult(
        overall_status=overall,
        criteria=criteria_results,
        failed_criteria=failed,
        regeneration_instructions=regen_instructions,
    )


# ======================================================================= #
#  LLM-based evaluation
# ======================================================================= #

def _get_evaluator_llm():
    kwargs = {
        "model": config.EVALUATOR_MODEL,
        "temperature": config.EVALUATOR_TEMPERATURE,
        "api_key": config.get_active_api_key(),
    }
    base_url = config.get_active_base_url()
    if base_url:
        kwargs["base_url"] = base_url
    return ChatOpenAI(**kwargs)


def _parse_llm_evaluation(raw_json: str, lesson_content: str) -> EvaluationResult:
    """
    Parse and validate the LLM's JSON evaluation response.

    Falls back to mock evaluation if JSON is malformed.
    Also applies a safety-net check for the retraining error regardless
    of what the LLM returned.
    """
    try:
        # Strip any markdown fences the LLM may have added despite instructions
        clean = raw_json.strip()
        if clean.startswith("```"):
            clean = re.sub(r"^```(?:json)?\s*", "", clean)
            clean = re.sub(r"\s*```$", "", clean)

        data: Dict[str, Any] = json.loads(clean)

        criteria = [
            CriterionResult(
                criterion=c["criterion"],
                status=Status(c["status"]),
                reason=c.get("reason", ""),
                evidence=c.get("evidence", ""),
                suggestion=c.get("suggestion", ""),
            )
            for c in data.get("criteria", [])
        ]

        # Safety net: if the lesson contains a retraining error, force FAIL
        if _contains_retrain_error(lesson_content):
            for criterion in criteria:
                if criterion.criterion == "Technical Accuracy" and criterion.status == Status.PASS:
                    logger.warning(
                        "Evaluator safety net: overriding Technical Accuracy to FAIL "
                        "because lesson contains retraining misinformation."
                    )
                    # Rebuild with corrected status
                    criteria = [
                        CriterionResult(
                            criterion=c.criterion,
                            status=Status.FAIL if c.criterion == "Technical Accuracy" else c.status,
                            reason=(
                                "SAFETY NET: Lesson incorrectly states RAG retrains the LLM. "
                                "RAG retrieves documents at inference time; it does not modify model weights."
                            ) if c.criterion == "Technical Accuracy" else c.reason,
                            evidence=c.evidence,
                            suggestion=(
                                "Remove the claim that RAG retrains/fine-tunes the LLM on new documents. "
                                "Clarify that RAG retrieves and passes document content in the prompt at inference time."
                            ) if c.criterion == "Technical Accuracy" else c.suggestion,
                        )
                        for c in criteria
                    ]
                    break

        failed = [c.criterion for c in criteria if c.status == Status.FAIL]
        overall = Status.PASS if not failed else Status.FAIL

        return EvaluationResult(
            overall_status=overall,
            criteria=criteria,
            failed_criteria=failed,
            regeneration_instructions=[
                c.suggestion for c in criteria if c.status == Status.FAIL and c.suggestion
            ],
        )

    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        logger.error("Evaluator: failed to parse LLM response — %s. Falling back to mock.", exc)
        return _build_mock_evaluation(lesson_content)


# ======================================================================= #
#  Public evaluation function
# ======================================================================= #

def evaluate_lesson(lesson_content: str, topic: str) -> EvaluationResult:
    """
    Evaluate the lesson against the seven-criterion rubric.

    Parameters
    ----------
    lesson_content : str
        The full Markdown lesson text.
    topic : str
        The topic the lesson is about (used in the prompt).

    Returns
    -------
    EvaluationResult
        Structured evaluation with per-criterion results.
    """
    logger.info("Evaluator: starting evaluation for topic '%s'", topic)

    if config.effective_mock_mode():
        logger.info("Evaluator: running in MOCK mode (rule-based).")
        result = _build_mock_evaluation(lesson_content)
        logger.info("Evaluator: overall status = %s", result.overall_status)
        return result

    # ---- Real LLM call ----
    llm = _get_evaluator_llm()
    user_prompt = build_evaluator_user_prompt(lesson_content=lesson_content, topic=topic)

    messages = [
        SystemMessage(content=EVALUATOR_SYSTEM_PROMPT),
        HumanMessage(content=user_prompt),
    ]

    logger.debug("Evaluator: calling LLM with model '%s'", config.EVALUATOR_MODEL)
    response = llm.invoke(messages)
    raw: str = response.content.strip()  # type: ignore[union-attr]

    result = _parse_llm_evaluation(raw, lesson_content)
    logger.info("Evaluator: overall status = %s, failed = %s", result.overall_status, result.failed_criteria)
    return result
