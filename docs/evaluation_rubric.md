# Evaluation Rubric — AI Lesson Studio

## Overview

The evaluator checks every generated lesson against **7 criteria**.  
Each criterion receives exactly **PASS** or **FAIL** — no partial scores.  
The overall result is **PASS only when ALL 7 criteria pass**.

The rubric is defined in `rubric.py` and is **immutable at runtime**.  
The self-improvement mechanism updates generator prompts only — never the rubric.

---

## Criterion 1: Technical Accuracy

**PASS requires:**
- RAG is explained correctly as retrieval + generation combined.
- Retrieval and generation are clearly distinguished.
- Embeddings and vector databases are described accurately.
- The RAG workflow is technically correct end-to-end.
- No major misleading or factually incorrect statements exist.

**FAIL if:**
- The explanation contains incorrect technical information.
- The lesson claims "RAG retrains the LLM when new documents are added" (incorrect).
- Important technical concepts are misunderstood or misrepresented.

> **Known test error:** "RAG retrains the LLM every time a new document is uploaded."  
> This is **factually incorrect**. RAG retrieves documents at inference time and does NOT modify model weights.

---

## Criterion 2: Beginner-Friendly Language

**PASS requires:**
- Language is simple and accessible.
- Sentences are short and easy to understand.
- Technical terms are explained immediately when introduced.
- A complete beginner with no AI background can follow the lesson.

**FAIL if:**
- Excessive advanced terminology is used without explanation.
- Important concepts are introduced but not explained.
- The explanation assumes prior AI or ML knowledge.

---

## Criterion 3: Practical Examples

**PASS requires:**
- At least two clear, understandable real-world examples are included.
- Examples concretely illustrate how RAG works.
- Examples connect abstract concepts to everyday situations.

**FAIL if:**
- No practical examples are present.
- Examples are present but do not explain the concept adequately.

---

## Criterion 4: Jargon Explanation

**PASS requires:**
- All important technical terms are explained in plain language.
- A glossary section is included.
- Terms such as 'embeddings', 'chunks', 'retrieval', and 'vector database' are explained simply.

**FAIL if:**
- Important technical terms appear without any explanation.
- No glossary is provided.

---

## Criterion 5: Key Topic Coverage

**PASS requires:**
- The full RAG pipeline is explained: document loading, chunking, embeddings, vector storage, retrieval, prompt augmentation, generation.
- Benefits of RAG over traditional LLMs are discussed.
- Limitations of RAG are discussed.

**FAIL if:**
- One or more critical pipeline steps are missing.
- Benefits or limitations are not discussed.

---

## Criterion 6: Teaching Flow and Structure

**PASS requires:**
- Content follows a logical sequence from basic to more advanced.
- Clear headings and subheadings are used.
- An introduction and a conclusion / key-takeaways section are present.
- The lesson is easy to follow from start to finish.

**FAIL if:**
- Concepts are disorganised or presented out of order.
- Important explanatory sections are missing.
- The lesson lacks an introduction or conclusion.

---

## Criterion 7: Knowledge Assessment

**PASS requires:**
- Exactly five multiple-choice questions are included.
- Every question has four answer options.
- Correct answers are clearly indicated.
- Short explanations accompany correct answers.
- Questions test actual lesson content.

**FAIL if:**
- Fewer than five questions are present.
- Questions lack four options.
- Correct answers or explanations are missing.
- Questions contain incorrect answers.

---

## Final Decision

| Condition | Outcome |
|---|---|
| All 7 criteria PASS | **APPROVED** — lesson is published |
| Any criterion FAILS (retries available) | **REGENERATE** — feedback sent to generator |
| Any criterion FAILS (no retries left) | **HUMAN REVIEW REQUIRED** |
