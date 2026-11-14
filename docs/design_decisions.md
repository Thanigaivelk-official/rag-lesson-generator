# Design Decisions — AI Lesson Studio

## Overview

This document explains the key architectural and technology choices made in building the Self-Evaluating AI Lesson Content Generator.

---

## 1. Why Python?

Python is the dominant language for AI and machine learning applications. The LangChain and LangGraph ecosystems are Python-first. The OpenAI SDK, Streamlit, and SQLite have excellent Python support. Python's readability makes the codebase accessible for review and future maintenance.

**Trade-off:** Python's GIL limits true parallelism, but this application is I/O-bound (LLM API calls), so this is not a practical limitation.

---

## 2. Why LangGraph?

LangGraph was chosen over simple sequential code or LangChain Chains for several reasons:

- **State management:** LangGraph's `StateGraph` maintains a typed, persistent state across nodes without manual variable threading.
- **Conditional routing:** The `add_conditional_edges` API makes the PASS/FAIL/RETRY branching explicit and auditable.
- **Cycle support:** Unlike LangChain's sequential chains, LangGraph supports cycles (required for the generate → evaluate → regenerate loop).
- **Termination guarantees:** Retry limits are enforced at the conditional edge level, preventing infinite loops by design.
- **Future extensibility:** Additional nodes (human-in-the-loop review, fact-checking, citation extraction) can be added without restructuring the workflow.

**Alternative considered:** A simple `while` loop. This would work but would not provide the state management, auditability, or extensibility of LangGraph.

---

## 3. Why Separate Generator and Evaluator?

Separating the generator and evaluator agents is the most critical architectural decision:

- **Independence:** The evaluator cannot "see" the generator's prompt or intent — it evaluates only what was produced.
- **No confirmation bias:** If the generator and evaluator shared context, the evaluator might be influenced by the generator's reasoning.
- **Separate models:** The generator uses a higher temperature (0.7) for creative content; the evaluator uses a lower temperature (0.1) for consistent, deterministic judgements.
- **Separate system prompts:** The evaluator's system prompt explicitly forbids passing criteria without evidence from the lesson text.
- **Safety net:** The evaluator has a rule-based override for known error patterns (the retraining misinformation) that cannot be bypassed by the generator.

---

## 4. Why Hard PASS/FAIL Criteria?

Numerical scoring (e.g., 7/10) was rejected because:

- **Ambiguity:** A score of 6/10 on Technical Accuracy is unclear — does it mean the lesson is publishable?
- **Threshold gaming:** A system might accumulate enough points across other criteria to "pass" even with a technically incorrect lesson.
- **Editorial accountability:** Binary decisions are easier to audit and explain to stakeholders.
- **Assessment alignment:** The brief explicitly requires PASS/FAIL — this is consistent with professional content moderation standards.

---

## 5. Why Maximum Two Retries?

The retry limit of 2 (configurable via `MAX_RETRIES`) balances quality improvement against cost and user experience:

- **Cost:** Each retry costs API credits. Three total attempts (1 initial + 2 retries) provide enough opportunity for improvement without excessive cost.
- **Diminishing returns:** If a lesson fails three consecutive times, the failure pattern likely requires human judgement or a prompt engineering fix, not another LLM retry.
- **Termination guarantee:** The limit ensures the system always terminates, regardless of LLM behaviour.
- **Human escalation:** Lessons that require human review are recorded for auditing, ensuring no bad content is silently approved.

**Configuration:** The limit is set via the `MAX_RETRIES` environment variable and can be increased for production use.

---

## 6. Why SQLite?

SQLite was chosen over PostgreSQL, MongoDB, or other databases because:

- **Zero infrastructure:** No separate server process, database credentials, or connection pool management required.
- **Portability:** A single `.db` file can be version-controlled (excluding sensitive data), shared, or inspected with standard tools.
- **Assessment appropriateness:** For a demonstration system processing one lesson at a time, SQLite's performance is more than sufficient.
- **Persistence:** Unlike in-memory dictionaries, SQLite persists across application restarts, satisfying the memory requirement.

**Production consideration:** For high-concurrency production use, migrate to PostgreSQL using the same `database.py` interface (switch `sqlite3` for `psycopg2` with minimal code changes).

---

## 7. How Self-Improvement Works

The self-improvement mechanism is transparent and auditable:

1. **Record:** Every failed criterion is recorded in `memory_patterns` with its reason and suggestion.
2. **Threshold:** When a criterion fails `FAILURE_THRESHOLD` times (default: 2), it triggers improvement generation.
3. **Generate:** A predefined improvement instruction for that criterion is saved to `prompt_improvements`.
4. **Apply:** On the next generation, `get_improvement_hints()` retrieves active improvements and injects them into the generator's prompt as "system improvement hints."
5. **Audit:** Every improvement is stored with a timestamp and application count in SQLite.

**What it does NOT do:**
- It does not modify the evaluator rubric or its pass/fail thresholds.
- It does not automatically approve content that previously failed.
- It does not dynamically rewrite its own improvement logic.

---

## 8. How Infinite Loops Are Prevented

Three complementary mechanisms prevent infinite loops:

1. **Retry counter:** `retry_count` is tracked in `AgentState`. The `decide_next` function routes to `human_review` when `retry_count >= MAX_RETRIES`.
2. **LangGraph termination:** The `approve` and `human_review` nodes both have edges to `END`, guaranteeing graph termination.
3. **Deterministic state transitions:** Each node produces a new state; there are no self-referential states that could cause unintended cycles.

---

## 9. Trade-offs and Limitations

| Trade-off | Decision | Rationale |
|---|---|---|
| Mock vs. real LLM | Support both via `MOCK_MODE` | Tests pass without API key; real key enables production use |
| In-process evaluation | LLM + rule-based fallback | LLM gives nuanced evaluation; rules provide safety net |
| SQLite concurrency | Accept single-writer limit | Appropriate for demo; scalable with PostgreSQL |
| Fixed improvement instructions | Predefined per criterion | Safe and auditable; dynamic generation could introduce errors |
| Streamlit session state | Use DB for persistence | Avoids session loss on page refresh |

---

## 10. How to Improve for Production

1. **Swap SQLite for PostgreSQL** for concurrent multi-user access.
2. **Add authentication** (e.g., Streamlit-Authenticator or Auth0) for the dashboard.
3. **Implement async LLM calls** using `langchain-openai`'s async methods to reduce latency.
4. **Add a human-in-the-loop node** where flagged lessons are routed to a human editor via email or Slack.
5. **Implement lesson versioning** to track how content evolves across retries.
6. **Add topic templates** for different subject areas beyond RAG.
7. **Deploy the Streamlit app** using Streamlit Cloud, Railway, or Docker with Nginx.
8. **Implement rate limiting** on the generation endpoint to control API costs.
9. **Add LLM output caching** (e.g., `langchain`'s `SQLiteCache`) to avoid regenerating identical lessons.
10. **Multi-language support** — extend the generator for regional Indian languages.
