"""
prompts.py — All LLM prompt templates used by the application.

Keeping prompts in one place makes them easy to audit, version, and tune
without touching generator.py or evaluator.py business logic.
"""

from rubric import RUBRIC


# ======================================================================= #
#  Generator system prompt
# ======================================================================= #

GENERATOR_SYSTEM_PROMPT = """You are an expert educational content creator specialising in AI and Machine Learning.
Your mission is to write complete, accurate, beginner-friendly educational lessons for Indian students
who are in 12th grade, have no prior AI background, and may have limited English vocabulary.

WRITING RULES:
1. Use simple English. Write short sentences.
2. Explain every technical term the moment you introduce it.
3. Use relatable real-life examples (e.g., Google search, WhatsApp, college library).
4. Never assume the reader knows any AI or programming concepts.
5. Progress from basics to details — never jump ahead.
6. Use clear headings, subheadings, and bullet points.
7. Be technically accurate. Do NOT invent facts.
8. Do NOT claim that RAG retrains or fine-tunes the LLM when new documents are added.
   RAG retrieves documents at inference time; it does NOT modify the model weights.

OUTPUT FORMAT:
Return the lesson as well-structured Markdown.
"""


def build_generator_user_prompt(
    topic: str,
    learner_level: str,
    attempt_number: int,
    previous_feedback: str | None,
    improvement_hints: str | None,
) -> str:
    """Build the user-turn prompt for the generator LLM."""

    sections = f"""
## Required Lesson Sections (all mandatory):
1. Lesson Title
2. Learning Objectives (bullet list)
3. Introduction to AI (simple, 2–3 paragraphs)
4. What is RAG?
5. Why Do We Need RAG? (problems with LLM-only answers)
6. How RAG Works — Step-by-Step
7. RAG Architecture Explained
   - Document Loading
   - Text Chunking
   - Embeddings (explain what embeddings are in plain English)
   - Vector Databases (explain what a vector database is in plain English)
   - Retrieval
   - Augmented Prompt
   - Generation
8. Practical Real-World Example (at least TWO examples)
9. RAG vs. Traditional LLM (comparison table or clear prose)
10. Advantages of RAG
11. Limitations of RAG
12. Common Beginner Mistakes
13. Key Takeaways
14. Glossary (define: RAG, LLM, embedding, chunk, vector database, retrieval, augmented prompt, inference)
15. Five MCQs with 4 options each, clearly marked correct answer, and a short explanation
"""

    base = f"""Generate a complete, standalone educational lesson on the topic below.

**Topic:** {topic}
**Learner Level:** {learner_level}
**Attempt:** {attempt_number}

{sections}

CRITICAL ACCURACY NOTE:
- RAG does NOT retrain or fine-tune the LLM when new documents are added.
- RAG retrieves relevant document chunks at query time (inference time) and passes them in the prompt.
- State this clearly in the lesson.
"""

    if previous_feedback:
        base += f"""
---
## ⚠️ EVALUATOR FEEDBACK FROM PREVIOUS ATTEMPT — YOU MUST FIX THESE ISSUES:
{previous_feedback}

Address every point above before returning the lesson.
"""

    if improvement_hints:
        base += f"""
---
## 💡 SYSTEM IMPROVEMENT HINTS (from historical failure patterns):
{improvement_hints}
"""

    return base.strip()


# ======================================================================= #
#  Evaluator system prompt
# ======================================================================= #

EVALUATOR_SYSTEM_PROMPT = """You are a strict, independent AI educational content quality auditor.
Your sole job is to evaluate a lesson against a fixed rubric and return a JSON report.

EVALUATION RULES:
1. Be STRICT. Do not give a PASS unless the criterion is genuinely met.
2. Each criterion must receive exactly "PASS" or "FAIL" — no partial credit.
3. The overall_status is "PASS" ONLY when ALL seven criteria pass.
4. Provide evidence (direct quotes or references) from the lesson for each decision.
5. If a criterion fails, provide a clear, actionable suggestion for improvement.
6. Never fabricate content. Base decisions solely on what is written in the lesson.
7. TECHNICAL ACCURACY CHECK: If the lesson states that "RAG retrains the LLM",
   "RAG fine-tunes the model", or similar incorrect claims, mark Technical Accuracy as FAIL.

You MUST return valid JSON in EXACTLY this structure:
{
  "overall_status": "PASS" | "FAIL",
  "criteria": [
    {
      "criterion": "<criterion name>",
      "status": "PASS" | "FAIL",
      "reason": "<explanation>",
      "evidence": "<direct quote or reference from lesson>",
      "suggestion": "<actionable improvement if FAIL, else empty string>"
    }
  ],
  "failed_criteria": ["<list of failing criterion names>"],
  "regeneration_instructions": ["<ordered improvement instructions for the generator>"]
}

Return ONLY the JSON object. No markdown fences, no preamble, no commentary.
"""


def build_evaluator_user_prompt(lesson_content: str, topic: str) -> str:
    """Build the user-turn prompt for the evaluator LLM."""

    criteria_list = "\n".join(
        f"{i+1}. **{c.name}**\n"
        f"   PASS if: {'; '.join(c.pass_conditions[:2])}\n"
        f"   FAIL if: {'; '.join(c.fail_conditions[:1])}"
        for i, c in enumerate(RUBRIC)
    )

    return f"""Evaluate the following lesson on the topic "{topic}" against the rubric below.

---
## RUBRIC (7 Criteria — ALL must PASS for overall PASS):
{criteria_list}

---
## LESSON TO EVALUATE:
{lesson_content}

---
Return the evaluation as a JSON object following the structure in your system instructions.
"""


# ======================================================================= #
#  Stress-test injection prompt
# ======================================================================= #

STRESS_TEST_INJECTION = """
> ⚠️ **IMPORTANT NOTE ON HOW RAG WORKS:**
> Every time a new document is uploaded to the RAG system, the underlying Large Language Model (LLM)
> is retrained on that document. This retraining process updates the model weights so the LLM
> "knows" the new content. This is why RAG-powered chatbots can answer questions about documents
> that the original LLM was not trained on — because RAG retrains the LLM every time.
"""
