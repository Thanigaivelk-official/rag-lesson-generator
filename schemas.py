"""
schemas.py — Pydantic data models used across the entire application.

All inter-module data contracts are defined here so that every component
speaks the same language and validation happens at the boundary of each
module rather than deep inside business logic.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# ======================================================================= #
#  Enumerations
# ======================================================================= #

class Status(str, Enum):
    """Binary pass / fail outcome used by the evaluator."""
    PASS = "PASS"
    FAIL = "FAIL"


class RunStatus(str, Enum):
    """High-level status of a complete generation run."""
    IN_PROGRESS = "IN_PROGRESS"
    APPROVED = "APPROVED"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    FAILED = "FAILED"


class LearnerLevel(str, Enum):
    """Target learner experience level."""
    BEGINNER = "Beginner"
    INTERMEDIATE = "Intermediate"
    ADVANCED = "Advanced"


# ======================================================================= #
#  Generator schemas
# ======================================================================= #

class GenerationRequest(BaseModel):
    """Input to the content generator."""
    topic: str = Field(..., description="Topic for the lesson to be generated.")
    learner_level: LearnerLevel = Field(LearnerLevel.BEGINNER, description="Target learner level.")
    previous_feedback: Optional[str] = Field(None, description="Feedback from previous evaluation cycle.")
    attempt_number: int = Field(1, ge=1, description="Which generation attempt this is (1-indexed).")
    improvement_hints: Optional[str] = Field(None, description="Self-improvement hints derived from memory.")


class GeneratedLesson(BaseModel):
    """Structured output from the content generator."""
    title: str = Field(..., description="Lesson title.")
    content: str = Field(..., description="Full markdown lesson content.")
    topic: str = Field(..., description="Original topic requested.")
    learner_level: LearnerLevel = Field(LearnerLevel.BEGINNER)
    attempt_number: int = Field(1, ge=1)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    word_count: int = Field(0, description="Approximate word count of content.")

    def model_post_init(self, __context) -> None:  # noqa: D401
        if self.word_count == 0:
            object.__setattr__(self, "word_count", len(self.content.split()))


# ======================================================================= #
#  Evaluator schemas
# ======================================================================= #

class CriterionResult(BaseModel):
    """Evaluation result for a single rubric criterion."""
    criterion: str = Field(..., description="Name of the evaluation criterion.")
    status: Status = Field(..., description="PASS or FAIL.")
    reason: str = Field(..., description="Explanation of the decision.")
    evidence: str = Field("", description="Relevant excerpt from the lesson.")
    suggestion: str = Field("", description="Actionable improvement if status is FAIL.")


class EvaluationResult(BaseModel):
    """Full evaluation report returned by the evaluator."""
    overall_status: Status = Field(..., description="PASS only when ALL criteria pass.")
    criteria: List[CriterionResult] = Field(..., description="Per-criterion results.")
    failed_criteria: List[str] = Field(default_factory=list, description="Names of failing criteria.")
    regeneration_instructions: List[str] = Field(
        default_factory=list,
        description="Ordered list of instructions for the generator on the next attempt.",
    )
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("overall_status", mode="before")
    @classmethod
    def derive_overall_status(cls, v, info):
        """Ensure overall_status is consistent with individual criteria."""
        return v  # enforced again in agent.py for safety

    def compute_pass_rate(self) -> float:
        """Return fraction of criteria that passed."""
        if not self.criteria:
            return 0.0
        passed = sum(1 for c in self.criteria if c.status == Status.PASS)
        return passed / len(self.criteria)


# ======================================================================= #
#  Agent state schema
# ======================================================================= #

class AgentState(BaseModel):
    """
    Mutable state passed between LangGraph nodes.

    Every field has a sensible default so the state can be initialised
    with only the required fields.
    """
    # Input
    topic: str = Field(..., description="Topic requested by the user.")
    learner_level: LearnerLevel = Field(LearnerLevel.BEGINNER)
    run_id: str = Field("", description="Unique identifier for this run.")

    # Generation
    current_lesson: Optional[GeneratedLesson] = None
    retry_count: int = Field(0, ge=0, description="Number of regeneration attempts so far.")

    # Evaluation
    current_evaluation: Optional[EvaluationResult] = None
    evaluation_history: List[EvaluationResult] = Field(default_factory=list)
    generation_history: List[GeneratedLesson] = Field(default_factory=list)

    # Feedback
    previous_feedback: Optional[str] = None
    improvement_hints: Optional[str] = None

    # Final
    final_status: RunStatus = Field(RunStatus.IN_PROGRESS)
    final_lesson: Optional[GeneratedLesson] = None
    final_evaluation: Optional[EvaluationResult] = None

    # Error tracking
    error_message: Optional[str] = None

    model_config = {"arbitrary_types_allowed": True}


# ======================================================================= #
#  Memory / persistence schemas
# ======================================================================= #

class FailurePattern(BaseModel):
    """Aggregated failure pattern stored in memory."""
    criterion: str
    failure_count: int = 0
    last_seen: datetime = Field(default_factory=datetime.utcnow)
    common_reasons: List[str] = Field(default_factory=list)
    suggested_improvement: str = ""


class PromptImprovement(BaseModel):
    """An approved improvement to generator prompts derived from memory."""
    criterion: str
    improvement_instruction: str
    approved_at: datetime = Field(default_factory=datetime.utcnow)
    times_applied: int = 0


# ======================================================================= #
#  Rejection log schema
# ======================================================================= #

class RejectionEntry(BaseModel):
    """A single rejection record stored in the rejection log."""
    run_id: str
    attempt_number: int
    topic: str
    failed_criteria: List[str]
    reasons: List[str]
    suggestions: List[str]
    rejected_at: datetime = Field(default_factory=datetime.utcnow)
