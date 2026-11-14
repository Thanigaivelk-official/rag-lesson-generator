"""
memory.py — Persistent memory and self-improvement module.

Responsible for:
  1. Storing failure patterns across runs.
  2. Identifying frequently failing criteria.
  3. Generating improvement hints for the generator.
  4. Saving and retrieving approved prompt improvements.
  5. Ensuring the system learns from repeated failures without
     ever modifying the evaluator rubric.
"""

import logging
from typing import List, Optional

import database as db

logger = logging.getLogger(__name__)

# Threshold: a criterion must fail this many times before a hint is generated.
FAILURE_THRESHOLD = 2


# ======================================================================= #
#  Recording failures
# ======================================================================= #

def record_evaluation_failures(
    criteria_results: List[dict],
    topic: str,
) -> None:
    """
    Persist failure patterns from a completed evaluation.

    Parameters
    ----------
    criteria_results : List[dict]
        The 'criteria' list from EvaluationResult (as dicts).
    topic : str
        The topic of the lesson being evaluated (for context).
    """
    for criterion in criteria_results:
        if criterion.get("status") == "FAIL":
            criterion_name = criterion.get("criterion", "Unknown")
            reason = criterion.get("reason", "")
            suggestion = criterion.get("suggestion", "")

            db.upsert_memory_pattern(
                criterion=criterion_name,
                reason=reason,
                suggestion=suggestion,
            )
            logger.info("Memory: recorded failure for criterion '%s'", criterion_name)


# ======================================================================= #
#  Retrieving improvement hints
# ======================================================================= #

def get_improvement_hints() -> Optional[str]:
    """
    Build a human-readable improvement hint string from stored patterns.

    Returns None if there are no patterns with failures above the threshold.
    """
    patterns = db.get_memory_patterns(min_failures=FAILURE_THRESHOLD)
    if not patterns:
        return None

    hints: List[str] = []
    for p in patterns:
        criterion = p["criterion"]
        count = p["failure_count"]
        suggestion = p.get("suggested_improvement", "")
        common_reasons = p.get("common_reasons_json", [])

        hint = f"⚠️  '{criterion}' has failed {count} time(s) in past runs."
        if common_reasons:
            hint += f" Common issue: {common_reasons[-1]}"
        if suggestion:
            hint += f" Recommended fix: {suggestion}"
        hints.append(hint)

    if not hints:
        return None

    return (
        "Based on past failures, pay extra attention to:\n"
        + "\n".join(f"  {i+1}. {h}" for i, h in enumerate(hints))
    )


# ======================================================================= #
#  Self-improvement: generating and storing prompt improvements
# ======================================================================= #

def generate_and_save_improvements() -> List[str]:
    """
    Inspect memory patterns and save new prompt-improvement instructions
    when a criterion has failed enough times.

    Returns a list of new improvement instructions that were saved.
    """
    patterns = db.get_memory_patterns(min_failures=FAILURE_THRESHOLD)
    existing_improvements = {
        imp["criterion"] for imp in db.get_prompt_improvements()
    }

    new_instructions: List[str] = []

    improvement_map = {
        "Beginner-Friendly Language": (
            "Use ONLY simple, everyday English. Every sentence must be understandable "
            "by a 12th-grade student with no AI background. Replace every technical term "
            "with a plain-English explanation immediately when you introduce it."
        ),
        "Practical Examples": (
            "Include AT LEAST THREE real-world examples that show exactly how RAG works in "
            "daily life. Use examples from Google Search, college libraries, hospital records, "
            "or customer support chatbots."
        ),
        "Jargon Explanation": (
            "Add a GLOSSARY section that defines every technical term in one simple sentence. "
            "Required terms: RAG, LLM, embedding, chunk, vector database, retrieval, "
            "augmented prompt, inference."
        ),
        "Technical Accuracy": (
            "Double-check all technical facts. Never say RAG retrains the LLM. "
            "RAG retrieves documents at inference time and passes them in the prompt — "
            "it does NOT modify model weights."
        ),
        "Key Topic Coverage": (
            "Explicitly cover ALL pipeline steps: document loading, text chunking, "
            "embedding generation, vector database storage, retrieval, prompt augmentation, "
            "and final generation. Use a numbered list or diagram description."
        ),
        "Teaching Flow and Structure": (
            "Start with an Introduction, end with a Conclusion / Key Takeaways section. "
            "Every concept must build on the previous one. Use numbered headings."
        ),
        "Knowledge Assessment": (
            "Include EXACTLY 5 MCQs. Each question must have 4 options labelled A, B, C, D. "
            "Mark the correct answer with '✓ Correct:' and add a one-sentence explanation."
        ),
    }

    for p in patterns:
        criterion = p["criterion"]
        if criterion in existing_improvements:
            continue  # already saved an improvement for this criterion

        instruction = improvement_map.get(criterion)
        if instruction:
            db.save_prompt_improvement(criterion=criterion, instruction=instruction)
            new_instructions.append(f"{criterion}: {instruction}")
            logger.info("Memory: saved new prompt improvement for '%s'", criterion)

    return new_instructions


# ======================================================================= #
#  Summary helper (used by the Streamlit dashboard)
# ======================================================================= #

def get_memory_summary() -> dict:
    """Return a summary dict for display in the UI."""
    patterns = db.get_memory_patterns(min_failures=1)
    improvements = db.get_prompt_improvements()
    return {
        "total_patterns": len(patterns),
        "patterns": patterns,
        "total_improvements": len(improvements),
        "improvements": improvements,
        "hint": get_improvement_hints(),
    }
