# Architecture: Self-Evaluating AI Lesson Content Generator

## System Overview

The **AI Lesson Studio** is a fully agentic GenAI application that generates educational content, independently evaluates it against a strict quality rubric, regenerates it when it fails, maintains persistent memory across sessions, and self-improves based on historical failure patterns.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Streamlit UI (app.py)                    │
│   Dashboard │ Generate │ Evaluation │ Rejection │ Memory │ Arch  │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LangGraph Agent (agent.py)                   │
│                                                                 │
│  generate_node ──► evaluate_node ──┬─► approve_node            │
│       ▲                            │                            │
│       │                            ├─► prepare_feedback_node   │
│       └────────────────────────────┘                            │
│                                    └─► human_review_node       │
└──────┬───────────────┬──────────────────────────────────────────┘
       │               │
       ▼               ▼
┌──────────────┐  ┌──────────────┐
│ Generator    │  │ Evaluator    │
│ (generator.py│  │ (evaluator.py│
│              │  │              │
│ OpenAI LLM   │  │ OpenAI LLM   │
│ + Mock mode  │  │ + Rule-based │
└──────────────┘  └──────────────┘
       │               │
       ▼               ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Memory Layer (memory.py)                      │
│   Failure patterns │ Improvement hints │ Prompt improvements   │
└──────────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                   SQLite Database (database.py)                 │
│   runs │ generations │ evaluations │ rejection_logs             │
│   memory_patterns │ prompt_improvements                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## LangGraph Workflow

```
START
  │
  ▼
[generate_node]
  │  Calls generator.py with topic, learner level,
  │  previous feedback, and memory-based hints.
  │  Saves generation to DB.
  │
  ▼
[evaluate_node]
  │  Calls evaluator.py independently.
  │  Checks 7 criteria with PASS/FAIL.
  │  Saves evaluation and rejection log to DB.
  │  Updates memory patterns.
  │
  ▼
[decide_next]  ──── PASS ────────────────────► [approve_node]
  │                                                  │
  │                                                  ▼
  │                                               [END]
  │
  ├──── FAIL + retries available ──► [prepare_feedback_node]
  │                                        │
  │                                        │  Compiles evaluator feedback.
  │                                        │  Triggers self-improvement analysis.
  │                                        ▼
  │                                   [generate_node]  (retry)
  │
  └──── FAIL + no retries ──────────► [human_review_node]
                                            │
                                            ▼
                                         [END]
```

---

## Component Responsibilities

| Component | File | Key Responsibilities |
|---|---|---|
| Streamlit UI | `app.py` | User interface, 7 navigation sections, downloads |
| LangGraph Agent | `agent.py` | Workflow orchestration, state management, termination |
| Content Generator | `generator.py` | LLM-based lesson creation, mock mode |
| Quality Evaluator | `evaluator.py` | 7-criterion evaluation, safety-net checks |
| Rubric | `rubric.py` | Immutable criterion definitions |
| Prompts | `prompts.py` | All LLM prompt templates |
| Memory | `memory.py` | Failure tracking, improvement hint generation |
| Database | `database.py` | SQLite CRUD, all 6 table operations |
| Schemas | `schemas.py` | Pydantic models for all data contracts |
| Config | `config.py` | Environment variable loading |

---

## Database Schema

```
runs                      generations              evaluations
────────────────          ─────────────────        ─────────────────────
id (PK)                   id (PK, AUTO)            id (PK, AUTO)
topic                     run_id (FK)              run_id (FK)
learner_level             attempt_number           attempt_number
status                    title                    overall_status
retry_count               content                  criteria_json
final_status              word_count               failed_criteria_json
created_at                created_at               regen_instructions_json
completed_at                                       evaluated_at

rejection_logs            memory_patterns          prompt_improvements
────────────────          ─────────────────        ─────────────────────
id (PK, AUTO)             id (PK, AUTO)            id (PK, AUTO)
run_id (FK)               criterion (UNIQUE)       criterion
attempt_number            failure_count            improvement_instruction
topic                     last_seen                approved_at
failed_criteria           common_reasons_json      times_applied
reasons_json              suggested_improvement
suggestions_json
rejected_at
```
