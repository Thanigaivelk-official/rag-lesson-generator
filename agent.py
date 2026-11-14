"""
agent.py — LangGraph agentic workflow.

Implements the full generation → evaluation → retry → approve/reject
cycle using LangGraph's StateGraph. The workflow:

  START
    ↓
  generate_lesson_node
    ↓
  evaluate_lesson_node
    ↓
  decide_next  ─── PASS ──→ approve_node ──→ END
                │
                └── FAIL + retries left ──→ prepare_feedback_node ──→ generate_lesson_node
                │
                └── FAIL + no retries ──→ human_review_node ──→ END
"""

import logging
import uuid
from typing import Literal

from langgraph.graph import StateGraph, END

import database as db
import memory as mem
from config import config
from evaluator import evaluate_lesson
from generator import generate_lesson
from schemas import (
    AgentState,
    EvaluationResult,
    GeneratedLesson,
    GenerationRequest,
    LearnerLevel,
    RunStatus,
    Status,
)

logger = logging.getLogger(__name__)


# ======================================================================= #
#  Graph nodes
# ======================================================================= #

def generate_lesson_node(state: dict) -> dict:
    """
    Node: call the content generator.
    Increments retry_count after the first attempt.
    """
    parsed = AgentState(**state)

    attempt = len(parsed.generation_history) + 1
    logger.info("Agent [generate]: attempt %d for '%s'", attempt, parsed.topic)

    # Fetch improvement hints from memory
    hints = mem.get_improvement_hints()

    request = GenerationRequest(
        topic=parsed.topic,
        learner_level=parsed.learner_level,
        attempt_number=attempt,
        previous_feedback=parsed.previous_feedback,
        improvement_hints=hints,
    )

    lesson: GeneratedLesson = generate_lesson(request)

    new_history = list(parsed.generation_history) + [lesson]
    retry_count = max(0, attempt - 1)  # first attempt = 0 retries

    # Persist to database
    db.save_generation(
        run_id=parsed.run_id,
        attempt_number=attempt,
        title=lesson.title,
        content=lesson.content,
        word_count=lesson.word_count,
    )

    return {
        **state,
        "current_lesson": lesson.model_dump(),
        "generation_history": [g.model_dump() for g in new_history],
        "retry_count": retry_count,
        "improvement_hints": hints,
    }


def evaluate_lesson_node(state: dict) -> dict:
    """
    Node: run the independent evaluator on the current lesson.
    """
    parsed = AgentState(**state)
    lesson_data = parsed.current_lesson
    if lesson_data is None:
        raise ValueError("evaluate_lesson_node called with no current_lesson in state.")

    lesson = GeneratedLesson(**lesson_data) if isinstance(lesson_data, dict) else lesson_data
    logger.info("Agent [evaluate]: evaluating attempt %d", lesson.attempt_number)

    evaluation: EvaluationResult = evaluate_lesson(
        lesson_content=lesson.content,
        topic=parsed.topic,
    )

    # Persist evaluation
    db.save_evaluation(
        run_id=parsed.run_id,
        attempt_number=lesson.attempt_number,
        overall_status=evaluation.overall_status.value,
        criteria=[c.model_dump() for c in evaluation.criteria],
        failed_criteria=evaluation.failed_criteria,
        regen_instructions=evaluation.regeneration_instructions,
    )

    new_eval_history = list(parsed.evaluation_history) + [evaluation]

    # Record failure patterns in memory
    if evaluation.overall_status == Status.FAIL:
        mem.record_evaluation_failures(
            criteria_results=[c.model_dump() for c in evaluation.criteria],
            topic=parsed.topic,
        )
        # Persist rejection log
        reasons = [
            c.reason for c in evaluation.criteria if c.status == Status.FAIL
        ]
        suggestions = [
            c.suggestion for c in evaluation.criteria if c.status == Status.FAIL and c.suggestion
        ]
        db.save_rejection(
            run_id=parsed.run_id,
            attempt_number=lesson.attempt_number,
            topic=parsed.topic,
            failed_criteria=evaluation.failed_criteria,
            reasons=reasons,
            suggestions=suggestions,
        )

    return {
        **state,
        "current_evaluation": evaluation.model_dump(),
        "evaluation_history": [e.model_dump() for e in new_eval_history],
    }


def decide_next(state: dict) -> Literal["approve", "retry", "human_review"]:
    """
    Conditional edge: decide the next node based on evaluation result.
    """
    parsed = AgentState(**state)
    evaluation_data = parsed.current_evaluation
    if evaluation_data is None:
        return "human_review"

    evaluation = EvaluationResult(**evaluation_data) if isinstance(evaluation_data, dict) else evaluation_data

    if evaluation.overall_status == Status.PASS:
        return "approve"

    if parsed.retry_count < config.MAX_RETRIES:
        return "retry"

    return "human_review"


def prepare_feedback_node(state: dict) -> dict:
    """
    Node: compile evaluator feedback into a structured message for
    the next generator call and trigger self-improvement.
    """
    parsed = AgentState(**state)
    evaluation_data = parsed.current_evaluation
    if evaluation_data is None:
        return state

    evaluation = EvaluationResult(**evaluation_data) if isinstance(evaluation_data, dict) else evaluation_data

    # Build feedback string
    feedback_lines = [
        f"The previous lesson failed evaluation. You MUST fix the following issues:\n"
    ]
    for i, instruction in enumerate(evaluation.regeneration_instructions, 1):
        feedback_lines.append(f"{i}. {instruction}")

    if evaluation.failed_criteria:
        feedback_lines.append(
            f"\nFailed criteria: {', '.join(evaluation.failed_criteria)}"
        )

    feedback = "\n".join(feedback_lines)

    # Trigger self-improvement — generate new prompt improvement rules if thresholds met
    new_improvements = mem.generate_and_save_improvements()
    if new_improvements:
        logger.info("Agent: %d new prompt improvements stored.", len(new_improvements))

    new_retry_count = parsed.retry_count + 1

    return {
        **state,
        "previous_feedback": feedback,
        "retry_count": new_retry_count,
    }


def approve_node(state: dict) -> dict:
    """
    Node: mark the run as APPROVED and persist the final lesson.
    """
    parsed = AgentState(**state)
    logger.info("Agent [approve]: lesson approved after %d retry(ies).", parsed.retry_count)

    db.update_run_status(parsed.run_id, RunStatus.APPROVED.value, parsed.retry_count)

    return {
        **state,
        "final_status": RunStatus.APPROVED.value,
        "final_lesson": parsed.current_lesson,
        "final_evaluation": parsed.current_evaluation,
    }


def human_review_node(state: dict) -> dict:
    """
    Node: mark the run as requiring human review (all retries exhausted).
    """
    parsed = AgentState(**state)
    logger.info(
        "Agent [human_review]: lesson requires human review after %d retry(ies).",
        parsed.retry_count,
    )

    db.update_run_status(parsed.run_id, RunStatus.HUMAN_REVIEW.value, parsed.retry_count)

    return {
        **state,
        "final_status": RunStatus.HUMAN_REVIEW.value,
        "final_lesson": parsed.current_lesson,
        "final_evaluation": parsed.current_evaluation,
    }


# ======================================================================= #
#  Graph construction
# ======================================================================= #

def build_graph() -> StateGraph:
    """Construct and compile the LangGraph StateGraph."""

    graph = StateGraph(dict)

    # Register nodes
    graph.add_node("generate", generate_lesson_node)
    graph.add_node("evaluate", evaluate_lesson_node)
    graph.add_node("prepare_feedback", prepare_feedback_node)
    graph.add_node("approve", approve_node)
    graph.add_node("human_review", human_review_node)

    # Entry point
    graph.set_entry_point("generate")

    # Edges
    graph.add_edge("generate", "evaluate")
    graph.add_conditional_edges(
        "evaluate",
        decide_next,
        {
            "approve": "approve",
            "retry": "prepare_feedback",
            "human_review": "human_review",
        },
    )
    graph.add_edge("prepare_feedback", "generate")
    graph.add_edge("approve", END)
    graph.add_edge("human_review", END)

    return graph.compile()


# ======================================================================= #
#  Public entry point
# ======================================================================= #

def run_agent(
    topic: str,
    learner_level: str = "Beginner",
    run_id: str | None = None,
    stress_test_content: str | None = None,
) -> dict:
    """
    Execute the full agentic workflow for a given topic.

    Parameters
    ----------
    topic : str
        The lesson topic.
    learner_level : str
        Target learner level string (e.g., 'Beginner').
    run_id : str | None
        Optional run identifier. Auto-generated if not provided.
    stress_test_content : str | None
        If provided, the first generation will use this content instead
        of calling the LLM (used by the deliberate error stress test).

    Returns
    -------
    dict
        The final agent state.
    """
    if run_id is None:
        run_id = str(uuid.uuid4())[:8].upper()

    level = LearnerLevel(learner_level) if isinstance(learner_level, str) else learner_level

    # Ensure database is ready and run row exists
    db.init_db()
    db.create_run(run_id=run_id, topic=topic, learner_level=level.value)

    initial_state = AgentState(
        topic=topic,
        learner_level=level,
        run_id=run_id,
    ).model_dump()

    # Stress-test injection: pre-populate current_lesson so the first
    # evaluate node sees the injected (faulty) content.
    if stress_test_content is not None:
        from schemas import GeneratedLesson
        from datetime import datetime
        injected = GeneratedLesson(
            title=f"[STRESS TEST] {topic}",
            content=stress_test_content,
            topic=topic,
            learner_level=level,
            attempt_number=1,
            generated_at=datetime.utcnow(),
        )
        db.save_generation(
            run_id=run_id,
            attempt_number=1,
            title=injected.title,
            content=injected.content,
            word_count=injected.word_count,
        )
        initial_state["current_lesson"] = injected.model_dump()
        initial_state["generation_history"] = [injected.model_dump()]

        # Build graph that skips the first generate node for stress tests
        graph = StateGraph(dict)
        graph.add_node("evaluate", evaluate_lesson_node)
        graph.add_node("generate", generate_lesson_node)
        graph.add_node("prepare_feedback", prepare_feedback_node)
        graph.add_node("approve", approve_node)
        graph.add_node("human_review", human_review_node)
        graph.set_entry_point("evaluate")
        graph.add_conditional_edges(
            "evaluate",
            decide_next,
            {
                "approve": "approve",
                "retry": "prepare_feedback",
                "human_review": "human_review",
            },
        )
        graph.add_edge("prepare_feedback", "generate")
        graph.add_edge("generate", "evaluate")
        graph.add_edge("approve", END)
        graph.add_edge("human_review", END)
        compiled = graph.compile()
    else:
        compiled = build_graph()

    logger.info("Agent: starting run %s for topic '%s'", run_id, topic)
    final_state = compiled.invoke(initial_state)
    logger.info("Agent: run %s completed with status '%s'", run_id, final_state.get("final_status"))

    return final_state
