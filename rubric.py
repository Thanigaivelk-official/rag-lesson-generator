"""
rubric.py — Evaluation rubric definitions.

This module defines the seven quality criteria used by the evaluator.
The rubric is kept separate from evaluator.py so it can be audited,
versioned, and updated by an administrator without touching business logic.

NOTE: These criteria are immutable at runtime. The self-improvement
mechanism updates generator *prompts*, never the rubric itself.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class RubricCriterion:
    """A single pass/fail criterion in the evaluation rubric."""
    name: str
    pass_conditions: List[str]
    fail_conditions: List[str]
    weight: int = 1  # Reserved for future weighted scoring (not used for PASS/FAIL)


# ======================================================================= #
#  The Seven Quality Criteria
# ======================================================================= #

RUBRIC: List[RubricCriterion] = [
    RubricCriterion(
        name="Technical Accuracy",
        pass_conditions=[
            "RAG is explained correctly as retrieval + generation combined.",
            "Retrieval and generation are clearly distinguished.",
            "Embeddings and vector databases are described accurately.",
            "The RAG workflow is technically correct end-to-end.",
            "No major misleading or factually incorrect statements exist.",
        ],
        fail_conditions=[
            "The explanation contains incorrect technical information.",
            "The workflow is misleading (e.g., claiming RAG retrains the LLM).",
            "Important technical concepts are misunderstood or misrepresented.",
        ],
    ),
    RubricCriterion(
        name="Beginner-Friendly Language",
        pass_conditions=[
            "Language is simple and accessible.",
            "Sentences are short and easy to understand.",
            "Technical terms are explained immediately when introduced.",
            "A complete beginner with no AI background can follow the lesson.",
        ],
        fail_conditions=[
            "Excessive advanced terminology is used without explanation.",
            "Important concepts are introduced but not explained.",
            "The explanation assumes prior AI or ML knowledge.",
        ],
    ),
    RubricCriterion(
        name="Practical Examples",
        pass_conditions=[
            "At least two clear, understandable real-world examples are included.",
            "Examples concretely illustrate how RAG works.",
            "Examples connect abstract concepts to everyday situations.",
        ],
        fail_conditions=[
            "No practical examples are present.",
            "Examples are present but do not explain the concept adequately.",
        ],
    ),
    RubricCriterion(
        name="Jargon Explanation",
        pass_conditions=[
            "All important technical terms are explained in plain language.",
            "A glossary section is included.",
            "Terms such as 'embeddings', 'chunks', 'retrieval', and 'vector database' are explained simply.",
        ],
        fail_conditions=[
            "Important technical terms appear without any explanation.",
            "No glossary is provided.",
        ],
    ),
    RubricCriterion(
        name="Key Topic Coverage",
        pass_conditions=[
            "The full RAG pipeline is explained: document loading, chunking, embeddings, vector storage, retrieval, prompt augmentation, generation.",
            "Benefits of RAG over traditional LLMs are discussed.",
            "Limitations of RAG are discussed.",
        ],
        fail_conditions=[
            "One or more critical pipeline steps are missing.",
            "Benefits or limitations are not discussed.",
        ],
    ),
    RubricCriterion(
        name="Teaching Flow and Structure",
        pass_conditions=[
            "Content follows a logical sequence from basic to more advanced.",
            "Clear headings and subheadings are used.",
            "An introduction and a conclusion / key-takeaways section are present.",
            "The lesson is easy to follow from start to finish.",
        ],
        fail_conditions=[
            "Concepts are disorganised or presented out of order.",
            "Important explanatory sections are missing.",
            "The lesson lacks an introduction or conclusion.",
        ],
    ),
    RubricCriterion(
        name="Knowledge Assessment",
        pass_conditions=[
            "Exactly five multiple-choice questions are included.",
            "Every question has four answer options.",
            "Correct answers are clearly indicated.",
            "Short explanations accompany correct answers.",
            "Questions test actual lesson content.",
        ],
        fail_conditions=[
            "Fewer than five questions are present.",
            "Questions lack four options.",
            "Correct answers or explanations are missing.",
            "Questions contain incorrect answers.",
        ],
    ),
]

# Human-readable rubric summary for prompt injection
RUBRIC_SUMMARY: str = "\n".join(
    f"- **{c.name}**: PASS requires {'; '.join(c.pass_conditions[:2])}."
    for c in RUBRIC
)

CRITERION_NAMES: List[str] = [c.name for c in RUBRIC]
