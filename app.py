"""
app.py — Streamlit dashboard for AI Lesson Studio.

Sections:
  1. Home / Overview
  2. Generate Lesson
  3. Evaluation Dashboard
  4. Rejection History
  5. Agent Memory
  6. System Architecture
  7. Settings
"""

import json
import logging
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

import streamlit as st
import pandas as pd

# ---- ensure project root is on PYTHONPATH ----
sys.path.insert(0, str(Path(__file__).parent))

from config import config
from schemas import LearnerLevel, RunStatus

# ======================================================================= #
#  Page config — MUST be first Streamlit call
# ======================================================================= #
st.set_page_config(
    page_title="AI Lesson Studio",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Lazy imports (after path is set)
import database as db
import memory as mem
from agent import run_agent
from prompts import STRESS_TEST_INJECTION

# Initialise database on startup
db.init_db()
config.ensure_dirs()

logging.basicConfig(level=getattr(logging, config.LOG_LEVEL, logging.INFO))
logger = logging.getLogger(__name__)


# ======================================================================= #
#  Custom CSS
# ======================================================================= #

st.markdown("""
<style>
/* ---- Global ---- */
html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; }

/* ---- Sidebar ---- */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #1e3a5f 100%);
    color: #e2e8f0;
}
[data-testid="stSidebar"] .stRadio label { color: #e2e8f0 !important; }
[data-testid="stSidebar"] h2 { color: #60a5fa; }

/* ---- Metric cards ---- */
.metric-card {
    background: linear-gradient(135deg, #1e3a5f, #0f172a);
    border-radius: 12px;
    padding: 20px;
    color: white;
    text-align: center;
    border: 1px solid #334155;
}
.metric-card .value { font-size: 2.5rem; font-weight: 700; color: #60a5fa; }
.metric-card .label { font-size: 0.85rem; color: #94a3b8; margin-top: 4px; }

/* ---- Status badges ---- */
.badge-pass {
    background:#16a34a; color:white; padding:3px 10px;
    border-radius:20px; font-size:0.8rem; font-weight:600;
}
.badge-fail {
    background:#dc2626; color:white; padding:3px 10px;
    border-radius:20px; font-size:0.8rem; font-weight:600;
}
.badge-review {
    background:#d97706; color:white; padding:3px 10px;
    border-radius:20px; font-size:0.8rem; font-weight:600;
}
.badge-inprogress {
    background:#2563eb; color:white; padding:3px 10px;
    border-radius:20px; font-size:0.8rem; font-weight:600;
}

/* ---- Section headers ---- */
.section-header {
    background: linear-gradient(90deg, #1e3a5f, transparent);
    border-left: 4px solid #60a5fa;
    padding: 10px 16px;
    border-radius: 4px;
    margin-bottom: 16px;
}
.section-header h3 { color: #60a5fa; margin: 0; }

/* ---- Progress bar ---- */
.stProgress > div > div { background-color: #2563eb; }

/* ---- Alert boxes ---- */
.alert-success {
    background:#f0fdf4; border:1px solid #16a34a; border-radius:8px;
    padding:16px; color:#15803d;
}
.alert-fail {
    background:#fef2f2; border:1px solid #dc2626; border-radius:8px;
    padding:16px; color:#dc2626;
}
.alert-warning {
    background:#fffbeb; border:1px solid #d97706; border-radius:8px;
    padding:16px; color:#b45309;
}
</style>
""", unsafe_allow_html=True)


# ======================================================================= #
#  Sidebar navigation
# ======================================================================= #

with st.sidebar:
    st.markdown("## 🎓 AI Lesson Studio")
    st.markdown("*Generate. Evaluate. Improve. Publish.*")
    st.divider()

    page = st.radio(
        "Navigation",
        options=[
            "🏠 Home",
            "✨ Generate Lesson",
            "📊 Evaluation Dashboard",
            "📋 Rejection History",
            "🧠 Agent Memory",
            "🏗️ System Architecture",
            "⚙️ Settings",
        ],
        label_visibility="collapsed",
    )

    st.divider()

    # API key status
    if config.is_api_key_configured():
        st.success(f"🟢 {config.LLM_PROVIDER.upper()} Connected")
    else:
        st.warning("🟡 Mock Mode Active")
        st.caption(f"Set {config.LLM_PROVIDER.upper()}_API_KEY in .env to enable real LLM calls.")

    st.caption(f"Provider: `{config.LLM_PROVIDER.upper()}`")
    st.caption(f"Model: `{config.GENERATOR_MODEL}`")
    st.caption(f"Max Retries: `{config.MAX_RETRIES}`")


# ======================================================================= #
#  Helper functions
# ======================================================================= #

def _status_badge(status: str) -> str:
    s = str(status).upper()
    if s == "PASS" or s == "APPROVED":
        return f'<span class="badge-pass">✅ {s}</span>'
    elif s in ("FAIL", "FAILED"):
        return f'<span class="badge-fail">❌ {s}</span>'
    elif s == "HUMAN_REVIEW":
        return f'<span class="badge-review">⚠️ HUMAN REVIEW</span>'
    else:
        return f'<span class="badge-inprogress">🔄 {s}</span>'


def _save_output(run_id: str, lesson_content: str, eval_data: dict | None) -> tuple[str, str]:
    """Save lesson and evaluation report to the outputs directory."""
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    lesson_path = Path(config.OUTPUT_DIR) / f"lesson_{run_id}_{ts}.md"
    eval_path = Path(config.OUTPUT_DIR) / f"evaluation_{run_id}_{ts}.json"

    lesson_path.write_text(lesson_content, encoding="utf-8")
    if eval_data:
        eval_path.write_text(json.dumps(eval_data, indent=2, default=str), encoding="utf-8")

    return str(lesson_path), str(eval_path)


# ======================================================================= #
#  Pages
# ======================================================================= #

# ------------------------------------------------------------------ #
#  HOME
# ------------------------------------------------------------------ #
if page == "🏠 Home":
    st.markdown("# 🎓 AI Lesson Studio")
    st.markdown("### *Generate. Evaluate. Improve. Publish.*")
    st.divider()

    # Summary metrics
    runs = db.get_all_runs()
    total = len(runs)
    approved = sum(1 for r in runs if r["final_status"] == "APPROVED")
    review = sum(1 for r in runs if r["final_status"] == "HUMAN_REVIEW")
    patterns = db.get_memory_patterns(min_failures=1)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Runs", total, help="Total generation runs initiated.")
    with col2:
        st.metric("✅ Approved", approved, help="Lessons that passed all criteria.")
    with col3:
        st.metric("⚠️ Human Review", review, help="Lessons that exhausted retries.")
    with col4:
        st.metric("🧠 Memory Patterns", len(patterns), help="Failure patterns tracked.")

    st.divider()

    col_left, col_right = st.columns([3, 2])
    with col_left:
        st.markdown("### 🔄 Agent Workflow")
        st.markdown("""
```
 START
   │
   ▼
 Generate Lesson (LLM)
   │
   ▼
 Evaluate Lesson (Independent LLM)
   │
   ├── ALL PASS ──────────────► Approve & Save ──► END
   │
   └── ANY FAIL
         │
         ├── Retries left? ──► Prepare Feedback ──► Generate Again
         │
         └── No retries left ──► Human Review Required ──► END
```
        """)

    with col_right:
        st.markdown("### ✨ Key Features")
        features = [
            ("🤖", "AI Content Generator", "Creates complete beginner-friendly lessons"),
            ("🔍", "Independent Evaluator", "7-criterion PASS/FAIL rubric"),
            ("🔄", "Auto-Regeneration", "Up to 2 retries with feedback"),
            ("🧠", "Persistent Memory", "Learns from past failures"),
            ("📋", "Rejection Logs", "Full audit trail"),
            ("🧪", "Stress Testing", "Deliberate error detection"),
        ]
        for icon, title, desc in features:
            st.markdown(f"**{icon} {title}**  \n{desc}")
            st.divider()

    # Recent runs table
    if runs:
        st.markdown("### 📜 Recent Runs")
        df = pd.DataFrame(runs[-10:][::-1])
        df_display = df[["id", "topic", "learner_level", "final_status", "retry_count", "created_at"]].rename(
            columns={
                "id": "Run ID", "topic": "Topic", "learner_level": "Level",
                "final_status": "Status", "retry_count": "Retries", "created_at": "Started"
            }
        )
        st.dataframe(df_display, use_container_width=True, hide_index=True)


# ------------------------------------------------------------------ #
#  GENERATE LESSON
# ------------------------------------------------------------------ #
elif page == "✨ Generate Lesson":
    st.markdown("# ✨ Generate Lesson")
    st.markdown("Configure your lesson and start the agentic workflow.")
    st.divider()

    with st.form("generation_form"):
        col1, col2 = st.columns([3, 1])
        with col1:
            topic = st.text_input(
                "Lesson Topic",
                value="Introduction to RAG (Retrieval-Augmented Generation)",
                help="Enter the topic for the lesson to be generated.",
            )
        with col2:
            learner_level = st.selectbox(
                "Learner Level",
                options=["Beginner", "Intermediate", "Advanced"],
                index=0,
            )

        st.markdown("#### 🧪 Stress Test Options")
        col_a, col_b = st.columns(2)
        with col_a:
            enable_stress_test = st.checkbox(
                "Enable Evaluator Stress Test",
                help="Inject a deliberate technical error to verify the evaluator catches it.",
            )
        with col_b:
            if enable_stress_test:
                st.info(
                    "Will inject: *'RAG retrains the LLM every time a new document is uploaded.'* "
                    "The evaluator must mark Technical Accuracy as FAIL."
                )

        submitted = st.form_submit_button("🚀 Start Generation", type="primary", use_container_width=True)

    if submitted:
        if not topic.strip():
            st.error("Please enter a topic.")
        else:
            run_id = str(uuid.uuid4())[:8].upper()
            st.markdown(f"**Run ID:** `{run_id}`")

            # Progress display
            status_placeholder = st.empty()
            progress_bar = st.progress(0)

            steps = []
            with st.spinner("Running agentic workflow…"):
                try:
                    # Determine stress-test content
                    stress_content = None
                    if enable_stress_test:
                        from prompts import STRESS_TEST_INJECTION
                        # Build a mostly-valid lesson but inject the error
                        from generator import MOCK_LESSON
                        stress_content = MOCK_LESSON + "\n\n" + STRESS_TEST_INJECTION

                    status_placeholder.info("🔄 Step 1/3: Generating lesson content…")
                    progress_bar.progress(20)

                    final_state = run_agent(
                        topic=topic,
                        learner_level=learner_level,
                        run_id=run_id,
                        stress_test_content=stress_content,
                    )

                    progress_bar.progress(70)
                    status_placeholder.info("🔍 Step 2/3: Evaluation complete. Processing results…")

                    final_status = final_state.get("final_status", "UNKNOWN")
                    retry_count = final_state.get("retry_count", 0)
                    final_lesson_data = final_state.get("final_lesson")
                    final_eval_data = final_state.get("final_evaluation")
                    eval_history = final_state.get("evaluation_history", [])
                    gen_history = final_state.get("generation_history", [])

                    progress_bar.progress(100)
                    status_placeholder.empty()

                    # ---- Results header ----
                    st.divider()
                    if final_status == RunStatus.APPROVED.value:
                        st.markdown('<div class="alert-success">✅ <strong>LESSON APPROVED</strong> — All 7 criteria passed.</div>', unsafe_allow_html=True)
                    elif final_status == RunStatus.HUMAN_REVIEW.value:
                        st.markdown('<div class="alert-warning">⚠️ <strong>HUMAN REVIEW REQUIRED</strong> — Lesson failed after all retries.</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="alert-fail">❌ <strong>FAILED</strong></div>', unsafe_allow_html=True)

                    st.markdown(f"**Attempts:** {len(gen_history)} &nbsp;|&nbsp; **Retries used:** {retry_count} / {config.MAX_RETRIES}")
                    st.divider()

                    # ---- Tabs for results ----
                    tab_lesson, tab_eval, tab_history, tab_stress = st.tabs(
                        ["📄 Lesson", "📊 Evaluation", "🔄 Attempt History", "🧪 Stress Test"]
                    )

                    with tab_lesson:
                        if final_lesson_data:
                            lesson_obj = final_lesson_data if isinstance(final_lesson_data, dict) else final_lesson_data.model_dump()
                            lesson_content = lesson_obj.get("content", "")
                            st.markdown(f"**Word count:** {lesson_obj.get('word_count', len(lesson_content.split()))}")
                            st.markdown("---")
                            st.markdown(lesson_content)
                            # Download
                            st.download_button(
                                "⬇️ Download Lesson (Markdown)",
                                data=lesson_content,
                                file_name=f"lesson_{run_id}.md",
                                mime="text/markdown",
                            )
                        else:
                            st.warning("No final lesson available.")

                    with tab_eval:
                        if final_eval_data:
                            eval_obj = final_eval_data if isinstance(final_eval_data, dict) else final_eval_data.model_dump()
                            overall = eval_obj.get("overall_status", "UNKNOWN")
                            st.markdown(f"**Overall Status:** {_status_badge(overall)}", unsafe_allow_html=True)
                            st.divider()
                            criteria = eval_obj.get("criteria", [])
                            for c in criteria:
                                col_s, col_c = st.columns([1, 5])
                                with col_s:
                                    st.markdown(_status_badge(c["status"]), unsafe_allow_html=True)
                                with col_c:
                                    with st.expander(f"**{c['criterion']}**"):
                                        st.markdown(f"**Reason:** {c['reason']}")
                                        if c.get("evidence"):
                                            st.markdown(f"**Evidence:** _{c['evidence']}_")
                                        if c.get("suggestion"):
                                            st.markdown(f"**Suggestion:** {c['suggestion']}")

                            # Download evaluation
                            st.download_button(
                                "⬇️ Download Evaluation Report (JSON)",
                                data=json.dumps(eval_obj, indent=2, default=str),
                                file_name=f"evaluation_{run_id}.json",
                                mime="application/json",
                            )
                        else:
                            st.warning("No evaluation data available.")

                    with tab_history:
                        st.markdown("### Generation & Evaluation History")
                        for i, (gen, ev) in enumerate(zip(gen_history, eval_history), 1):
                            gen_d = gen if isinstance(gen, dict) else gen.model_dump()
                            ev_d = ev if isinstance(ev, dict) else ev.model_dump()
                            with st.expander(f"Attempt {i} — {_status_badge(ev_d.get('overall_status','?'))}", expanded=(i == len(gen_history))):
                                st.markdown(f"**Word count:** {gen_d.get('word_count', '?')}")
                                st.markdown(f"**Failed criteria:** {', '.join(ev_d.get('failed_criteria', [])) or 'None'}")
                                if ev_d.get("regeneration_instructions"):
                                    st.markdown("**Regeneration instructions sent:**")
                                    for inst in ev_d["regeneration_instructions"]:
                                        st.markdown(f"- {inst}")

                    with tab_stress:
                        if enable_stress_test:
                            st.markdown("### 🧪 Evaluator Stress Test Report")
                            st.info("A deliberate technical error was injected into the first attempt.")
                            if eval_history:
                                first_eval = eval_history[0]
                                ev_d = first_eval if isinstance(first_eval, dict) else first_eval.model_dump()
                                st.markdown(f"**Attempt 1 Result:** {_status_badge(ev_d.get('overall_status','?'))}", unsafe_allow_html=True)
                                # Show Technical Accuracy criterion
                                for c in ev_d.get("criteria", []):
                                    if c.get("criterion") == "Technical Accuracy":
                                        st.markdown(f"**Technical Accuracy:** {_status_badge(c['status'])}", unsafe_allow_html=True)
                                        st.markdown(f"**Reason:** {c['reason']}")
                                        st.markdown(f"**Suggestion given to generator:** {c.get('suggestion','')}")
                                        break
                                st.markdown("---")
                                if len(eval_history) > 1:
                                    second_eval = eval_history[1]
                                    ev2 = second_eval if isinstance(second_eval, dict) else second_eval.model_dump()
                                    st.markdown(f"**Attempt 2 Result (after correction):** {_status_badge(ev2.get('overall_status','?'))}", unsafe_allow_html=True)
                        else:
                            st.info("Enable the stress test checkbox above to see this report.")

                except Exception as exc:
                    progress_bar.empty()
                    status_placeholder.empty()
                    st.error(f"An error occurred: {exc}")
                    logger.exception("Workflow error")


# ------------------------------------------------------------------ #
#  EVALUATION DASHBOARD
# ------------------------------------------------------------------ #
elif page == "📊 Evaluation Dashboard":
    st.markdown("# 📊 Evaluation Dashboard")
    st.divider()

    runs = db.get_all_runs()
    if not runs:
        st.info("No runs found. Generate a lesson first.")
    else:
        run_options = {r["id"]: f"{r['id']} — {r['topic'][:50]} [{r['final_status'] or 'IN_PROGRESS'}]" for r in runs}
        selected_id = st.selectbox("Select Run", options=list(run_options.keys()), format_func=lambda x: run_options[x])

        evaluations = db.get_evaluations_for_run(selected_id)
        generations = db.get_generations_for_run(selected_id)

        if not evaluations:
            st.warning("No evaluations found for this run.")
        else:
            for eval_row in evaluations:
                attempt = eval_row["attempt_number"]
                overall = eval_row["overall_status"]
                criteria = eval_row["criteria_json"]

                st.markdown(f"### Attempt {attempt} — {_status_badge(overall)}", unsafe_allow_html=True)

                # Pass rate
                passed = sum(1 for c in criteria if c["status"] == "PASS")
                total_c = len(criteria)
                pass_pct = int(passed / total_c * 100) if total_c else 0
                st.progress(pass_pct / 100, text=f"Pass rate: {passed}/{total_c} criteria ({pass_pct}%)")

                cols = st.columns(len(criteria))
                for col, c in zip(cols, criteria):
                    with col:
                        icon = "✅" if c["status"] == "PASS" else "❌"
                        st.markdown(f"**{icon}**  \n{c['criterion'].replace(' ', chr(10))}")

                with st.expander("View full evaluation details"):
                    for c in criteria:
                        st.markdown(f"**{c['criterion']}:** {_status_badge(c['status'])}", unsafe_allow_html=True)
                        st.markdown(f"> {c['reason']}")
                        if c.get("suggestion"):
                            st.markdown(f"💡 _{c['suggestion']}_")
                        st.divider()

                st.markdown("---")


# ------------------------------------------------------------------ #
#  REJECTION HISTORY
# ------------------------------------------------------------------ #
elif page == "📋 Rejection History":
    st.markdown("# 📋 Rejection History")
    st.markdown("Complete audit trail of all failed generation attempts.")
    st.divider()

    rejections = db.get_rejection_history(limit=100)
    if not rejections:
        st.info("No rejections recorded yet.")
    else:
        st.markdown(f"**Total rejection records:** {len(rejections)}")

        for r in rejections:
            with st.expander(
                f"Run `{r['run_id']}` | Attempt {r['attempt_number']} | Topic: {r['topic'][:50]}",
                expanded=False,
            ):
                st.markdown(f"**Rejected at:** {r['rejected_at']}")
                st.markdown(f"**Failed criteria:** `{r['failed_criteria']}`")
                st.markdown("**Reasons:**")
                for reason in r.get("reasons_json", []):
                    st.markdown(f"- {reason}")
                if r.get("suggestions_json"):
                    st.markdown("**Suggestions given:**")
                    for s in r["suggestions_json"]:
                        st.markdown(f"- 💡 {s}")


# ------------------------------------------------------------------ #
#  AGENT MEMORY
# ------------------------------------------------------------------ #
elif page == "🧠 Agent Memory":
    st.markdown("# 🧠 Agent Memory")
    st.markdown("Failure patterns and self-improvement instructions derived from past runs.")
    st.divider()

    summary = mem.get_memory_summary()

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Failure Patterns Tracked", summary["total_patterns"])
    with col2:
        st.metric("Prompt Improvements Saved", summary["total_improvements"])

    if summary["hint"]:
        st.markdown("### 💡 Current Improvement Hints")
        st.info(summary["hint"])

    st.divider()
    st.markdown("### 🔴 Failure Patterns")
    patterns = summary["patterns"]
    if not patterns:
        st.info("No failure patterns recorded yet. Run a few lessons to build memory.")
    else:
        for p in patterns:
            with st.expander(f"**{p['criterion']}** — Failed {p['failure_count']} time(s)"):
                st.markdown(f"**Last seen:** {p['last_seen']}")
                if p.get("common_reasons_json"):
                    st.markdown("**Common reasons:**")
                    for r in p["common_reasons_json"]:
                        st.markdown(f"- {r}")
                if p.get("suggested_improvement"):
                    st.markdown(f"**Stored suggestion:** {p['suggested_improvement']}")

    st.divider()
    st.markdown("### ✅ Approved Prompt Improvements")
    improvements = summary["improvements"]
    if not improvements:
        st.info("No improvements generated yet. Failure thresholds not yet reached.")
    else:
        for imp in improvements:
            with st.expander(f"**{imp['criterion']}** — applied {imp['times_applied']} time(s)"):
                st.markdown(f"**Instruction:** {imp['improvement_instruction']}")
                st.markdown(f"**Approved at:** {imp['approved_at']}")

    st.divider()
    if st.button("🔄 Trigger Self-Improvement Analysis"):
        new = mem.generate_and_save_improvements()
        if new:
            st.success(f"Generated {len(new)} new improvement instruction(s).")
            for n in new:
                st.markdown(f"- {n}")
        else:
            st.info("No new improvements needed at this time (thresholds not met or already saved).")


# ------------------------------------------------------------------ #
#  SYSTEM ARCHITECTURE
# ------------------------------------------------------------------ #
elif page == "🏗️ System Architecture":
    st.markdown("# 🏗️ System Architecture")
    st.divider()

    st.markdown("""
## Component Overview

| Component | File | Responsibility |
|---|---|---|
| **Streamlit UI** | `app.py` | User interface, dashboard, downloads |
| **Agent Orchestrator** | `agent.py` | LangGraph workflow, state management |
| **Content Generator** | `generator.py` | LLM-based lesson creation |
| **Quality Evaluator** | `evaluator.py` | Independent 7-criterion evaluation |
| **Rubric** | `rubric.py` | Immutable evaluation criteria |
| **Prompts** | `prompts.py` | All LLM prompt templates |
| **Memory** | `memory.py` | Failure patterns, self-improvement |
| **Database** | `database.py` | SQLite persistence layer |
| **Schemas** | `schemas.py` | Pydantic data contracts |
| **Config** | `config.py` | Environment variable management |

---

## LangGraph Workflow

```
START ──► generate ──► evaluate ──┬── [PASS] ──► approve ──► END
                     ▲             │
                     │             └── [FAIL + retries] ──► prepare_feedback ─┘
                     │
                     └── [FAIL + no retries] ──► human_review ──► END
```

---

## Database Schema

```
runs ──────────────────────────────────────────────────────────
  id | topic | learner_level | status | retry_count | timestamps

generations ───────────────────────────────────────────────────
  id | run_id | attempt_number | title | content | word_count

evaluations ────────────────────────────────────────────────────
  id | run_id | attempt_number | overall_status | criteria_json

rejection_logs ─────────────────────────────────────────────────
  id | run_id | attempt_number | topic | failed_criteria | reasons

memory_patterns ────────────────────────────────────────────────
  id | criterion | failure_count | last_seen | common_reasons

prompt_improvements ────────────────────────────────────────────
  id | criterion | improvement_instruction | times_applied
```

---

## Data Flow

```
User Input (topic, level)
        │
        ▼
   AgentState (Pydantic)
        │
        ├──► Generator (LLM) ──► GeneratedLesson
        │
        ├──► Evaluator (LLM) ──► EvaluationResult (7 criteria)
        │
        ├──► Memory (SQLite) ──► Failure patterns, improvements
        │
        └──► Database (SQLite) ──► Runs, generations, evaluations, rejections
```
    """)


# ------------------------------------------------------------------ #
#  SETTINGS
# ------------------------------------------------------------------ #
elif page == "⚙️ Settings":
    st.markdown("# ⚙️ Settings")
    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🔑 API Configuration")
        st.markdown(f"**Generator Model:** `{config.GENERATOR_MODEL}`")
        st.markdown(f"**Evaluator Model:** `{config.EVALUATOR_MODEL}`")
        st.markdown(f"**Generator Temperature:** `{config.GENERATOR_TEMPERATURE}`")
        st.markdown(f"**Evaluator Temperature:** `{config.EVALUATOR_TEMPERATURE}`")

        api_status = "✅ Configured" if config.is_api_key_configured() else "❌ Not configured (Mock Mode)"
        st.markdown(f"**API Key Status:** {api_status}")

        st.info(
            "To configure the API key, create a `.env` file in the project root "
            "and set `OPENAI_API_KEY=your_key_here`. See `.env.example` for a template."
        )

    with col2:
        st.markdown("### 🗄️ Database")
        st.markdown(f"**Database Path:** `{config.DATABASE_PATH}`")
        st.markdown(f"**Output Directory:** `{config.OUTPUT_DIR}`")
        st.markdown(f"**Max Retries:** `{config.MAX_RETRIES}`")
        st.markdown(f"**Mock Mode:** `{config.effective_mock_mode()}`")
        st.markdown(f"**Log Level:** `{config.LOG_LEVEL}`")

        if st.button("🗑️ Reset Database (clear all data)", type="secondary"):
            st.warning(
                "This will delete ALL runs, lessons, and evaluations. "
                "Type 'CONFIRM' below to proceed."
            )
            confirm = st.text_input("Confirmation")
            if confirm == "CONFIRM":
                db_path = Path(config.DATABASE_PATH)
                if db_path.exists():
                    db_path.unlink()
                db.init_db()
                st.success("Database reset successfully.")
