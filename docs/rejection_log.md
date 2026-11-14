# Example Rejection Log

This document shows a sample rejection log from the Evaluator Stress Test.

---

## RUN ID: STRESS01

### Attempt 1

**Topic:** Introduction to RAG (Retrieval-Augmented Generation)  
**Status:** ❌ FAIL  
**Timestamp:** 2026-11-14T08:30:00Z

**Injected Error:**
> "RAG retrains the LLM every time a new document is uploaded. This retraining process updates the model weights so the LLM 'knows' the new content."

**Failed Criteria:**
- Technical Accuracy

**Reason:**
- The lesson contains a critical technical error. It states that RAG retrains the LLM when new documents are added. This is factually incorrect. RAG retrieves documents at inference time and passes them in the prompt. The underlying LLM's weights are never modified when new documents are added to a RAG system.

**Feedback sent to generator:**
1. Remove the claim that RAG retrains or fine-tunes the LLM on new documents.
2. Clarify that RAG stores documents in a vector database and retrieves relevant chunks at query time (inference time).
3. Explicitly state that the LLM's model weights are NOT changed when new documents are added.
4. The correct explanation: "When a user asks a question, RAG retrieves relevant document chunks and passes them in the prompt to the LLM. The LLM then generates an answer using this retrieved context. No retraining occurs."

---

### Attempt 2

**Topic:** Introduction to RAG (Retrieval-Augmented Generation)  
**Status:** ✅ PASS  
**Timestamp:** 2026-11-14T08:31:45Z

**Changes made:**
- Removed incorrect retraining statement.
- Added explicit clarification: "RAG does NOT retrain or modify the LLM. When you add new documents to a RAG system, the LLM itself is not changed. Instead, those documents are stored in a special database, and when a question is asked, the system retrieves the relevant document chunks and passes them to the LLM in the prompt."
- Added comparison table: "RAG vs. Fine-tuning vs. Retraining."

**Evaluation Results:**
| Criterion | Status |
|---|---|
| Technical Accuracy | ✅ PASS |
| Beginner-Friendly Language | ✅ PASS |
| Practical Examples | ✅ PASS |
| Jargon Explanation | ✅ PASS |
| Key Topic Coverage | ✅ PASS |
| Teaching Flow and Structure | ✅ PASS |
| Knowledge Assessment | ✅ PASS |

**Final Decision: ✅ APPROVED**
