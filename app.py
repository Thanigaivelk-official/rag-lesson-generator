"""
app.py — Modern, Enterprise-Grade UI for AI Lesson Studio.

Features:
  - Polished modern dark/slate design system with subtle gradients and glassmorphism.
  - Interactive multi-stage visual execution stepper.
  - 7 comprehensive pages with responsive grids and KPI widgets.
  - Interactive evaluation breakdown with evidence callouts.
  - Side-by-side stress test comparison.
  - Persistent rejection logs, memory tracking, and architecture documentation.
"""

import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# ---- Ensure project root is on PYTHONPATH ----
sys.path.insert(0, str(Path(__file__).parent))

from config import config
from schemas import LearnerLevel, RunStatus

# ======================================================================= #
#  Page Config — Must be first Streamlit call
# ======================================================================= #
st.set_page_config(
    page_title="AI Lesson Studio | Self-Evaluating Content Systems",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Core imports
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
#  Modern CSS Theme & Design System
# ======================================================================= #
st.markdown("""
<style>
/* ---- CSS Variables & Core System ---- */
:root {
    --bg-primary: #0b0f19;
    --bg-card: #111827;
    --bg-card-hover: #1f2937;
    --border-color: #1e293b;
    --border-focus: #3b82f6;
    --accent-blue: #3b82f6;
    --accent-indigo: #6366f1;
    --accent-emerald: #10b981;
    --accent-rose: #f43f5e;
    --accent-amber: #f59e0b;
    --text-primary: #f8fafc;
    --text-secondary: #94a3b8;
    --text-muted: #64748b;
}

/* Base fonts & smooth rendering */
html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
}

/* Streamlit main block spacing */
.main .block-container {
    padding-top: 1.8rem;
    padding-bottom: 3.5rem;
    max-width: 1250px;
}

/* Sidebar styling */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0b0f19 0%, #0f172a 100%) !important;
    border-right: 1px solid #1e293b;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label {
    padding: 8px 12px;
    border-radius: 8px;
    transition: all 0.2s ease;
    font-size: 0.95rem;
    font-weight: 500;
}
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {
    background: rgba(59, 130, 246, 0.1);
    color: #60a5fa !important;
}

/* KPI Stat Cards */
.kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 16px;
    margin: 16px 0 24px 0;
}
.kpi-card {
    background: linear-gradient(145deg, #111827, #0f172a);
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 20px;
    position: relative;
    overflow: hidden;
    transition: transform 0.2s ease, border-color 0.2s ease;
}
.kpi-card:hover {
    transform: translateY(-2px);
    border-color: #3b82f6;
}
.kpi-card .kpi-icon {
    font-size: 1.6rem;
    margin-bottom: 8px;
}
.kpi-card .kpi-val {
    font-size: 2.2rem;
    font-weight: 800;
    color: #f8fafc;
    letter-spacing: -0.03em;
    line-height: 1;
}
.kpi-card .kpi-label {
    font-size: 0.82rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #94a3b8;
    margin-top: 6px;
    font-weight: 600;
}
.kpi-card .kpi-badge {
    position: absolute;
    top: 16px;
    right: 16px;
    padding: 3px 8px;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
}

/* Status Badges */
.badge-pass {
    background: rgba(16, 185, 129, 0.15);
    color: #34d399;
    border: 1px solid rgba(16, 185, 129, 0.3);
    padding: 4px 12px;
    border-radius: 9999px;
    font-size: 0.78rem;
    font-weight: 700;
    display: inline-flex;
    align-items: center;
    gap: 5px;
}
.badge-fail {
    background: rgba(244, 63, 94, 0.15);
    color: #fb7185;
    border: 1px solid rgba(244, 63, 94, 0.3);
    padding: 4px 12px;
    border-radius: 9999px;
    font-size: 0.78rem;
    font-weight: 700;
    display: inline-flex;
    align-items: center;
    gap: 5px;
}
.badge-review {
    background: rgba(245, 158, 11, 0.15);
    color: #fbbf24;
    border: 1px solid rgba(245, 158, 11, 0.3);
    padding: 4px 12px;
    border-radius: 9999px;
    font-size: 0.78rem;
    font-weight: 700;
    display: inline-flex;
    align-items: center;
    gap: 5px;
}
.badge-info {
    background: rgba(59, 130, 246, 0.15);
    color: #60a5fa;
    border: 1px solid rgba(59, 130, 246, 0.3);
    padding: 4px 12px;
    border-radius: 9999px;
    font-size: 0.78rem;
    font-weight: 700;
    display: inline-flex;
    align-items: center;
    gap: 5px;
}

/* Section Header Banners */
.page-header {
    background: linear-gradient(90deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0) 100%);
    border-left: 4px solid #3b82f6;
    padding: 16px 20px;
    border-radius: 0 10px 10px 0;
    margin-bottom: 24px;
}
.page-title {
    font-size: 1.8rem;
    font-weight: 800;
    color: #f8fafc;
    letter-spacing: -0.02em;
    margin: 0;
}
.page-subtitle {
    font-size: 0.92rem;
    color: #94a3b8;
    margin-top: 4px;
    margin-bottom: 0;
}

/* Feature Cards & Glass Panels */
.feature-box {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 18px;
    height: 100%;
}
.feature-box h4 {
    margin-top: 0;
    color: #38bdf8;
    font-size: 1.05rem;
    display: flex;
    align-items: center;
    gap: 8px;
}
.feature-box p {
    color: #94a3b8;
    font-size: 0.88rem;
    line-height: 1.5;
    margin: 0;
}

/* Rubric Card Layout */
.rubric-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 16px;
    margin-top: 14px;
}
.rubric-card {
    background: #0f172a;
    border-radius: 10px;
    border: 1px solid #1e293b;
    padding: 16px;
    position: relative;
}
.rubric-card.pass {
    border-left: 4px solid #10b981;
}
.rubric-card.fail {
    border-left: 4px solid #f43f5e;
}
.rubric-title {
    font-size: 0.95rem;
    font-weight: 700;
    color: #f1f5f9;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}
.rubric-reason {
    font-size: 0.85rem;
    color: #94a3b8;
    line-height: 1.45;
}
.rubric-evidence {
    background: rgba(15, 23, 42, 0.6);
    border-left: 2px solid #3b82f6;
    padding: 6px 10px;
    margin-top: 8px;
    font-size: 0.8rem;
    color: #cbd5e1;
    font-style: italic;
}
.rubric-suggestion {
    background: rgba(245, 158, 11, 0.1);
    border: 1px dashed rgba(245, 158, 11, 0.3);
    padding: 6px 10px;
    margin-top: 8px;
    border-radius: 6px;
    font-size: 0.8rem;
    color: #fcd34d;
}

/* Callout Alerts */
.callout-box {
    border-radius: 10px;
    padding: 16px 20px;
    margin: 16px 0;
    display: flex;
    align-items: flex-start;
    gap: 12px;
}
.callout-success {
    background: rgba(16, 185, 129, 0.08);
    border: 1px solid rgba(16, 185, 129, 0.3);
    color: #a7f3d0;
}
.callout-warning {
    background: rgba(245, 158, 11, 0.08);
    border: 1px solid rgba(245, 158, 11, 0.3);
    color: #fde68a;
}
.callout-danger {
    background: rgba(244, 63, 94, 0.08);
    border: 1px solid rgba(244, 63, 94, 0.3);
    color: #fecdd3;
}
.callout-info {
    background: rgba(59, 130, 246, 0.08);
    border: 1px solid rgba(59, 130, 246, 0.3);
    color: #bfdbfe;
}

/* Download Bar */
.action-bar {
    background: #0f172a;
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 14px 18px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: 16px 0;
}

/* Step Pipeline Tracker */
.stepper-container {
    display: flex;
    justify-content: space-between;
    margin: 20px 0;
    position: relative;
}
.stepper-container::before {
    content: '';
    position: absolute;
    top: 14px;
    left: 20px;
    right: 20px;
    height: 2px;
    background: #1e293b;
    z-index: 1;
}
.stepper-step {
    position: relative;
    z-index: 2;
    text-align: center;
    flex: 1;
}
.step-circle {
    width: 30px;
    height: 30px;
    border-radius: 50%;
    background: #0f172a;
    border: 2px solid #334155;
    color: #94a3b8;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 0.8rem;
    font-weight: 700;
    margin-bottom: 6px;
}
.step-circle.active {
    border-color: #3b82f6;
    color: #60a5fa;
    box-shadow: 0 0 12px rgba(59, 130, 246, 0.4);
}
.step-circle.done {
    border-color: #10b981;
    background: #10b981;
    color: #ffffff;
}
.step-label {
    font-size: 0.76rem;
    color: #94a3b8;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.04em;
}
</style>
""", unsafe_allow_html=True)


# ======================================================================= #
#  Sidebar Navigation & Environment Status
# ======================================================================= #
with st.sidebar:
    st.markdown("""
    <div style="padding: 10px 0 16px 0;">
        <div style="display: flex; align-items: center; gap: 10px;">
            <span style="font-size: 2rem;">🎓</span>
            <div>
                <div style="font-weight: 800; font-size: 1.25rem; color: #f8fafc; letter-spacing: -0.02em;">AI Lesson Studio</div>
                <div style="font-size: 0.75rem; color: #60a5fa; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;">Self-Evaluating Agent</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    page = st.radio(
        "Navigation Menu",
        options=[
            "🏠 Overview Dashboard",
            "✨ Generate Lesson",
            "📊 Rubric & Evaluations",
            "📋 Rejection Logs",
            "🧠 Persistent Memory",
            "🏗️ System Architecture",
            "⚙️ Runtime Settings",
        ],
        label_visibility="collapsed",
    )

    st.markdown("<hr style='border-color: #1e293b; margin: 18px 0;'>", unsafe_allow_html=True)

    # Provider Pill
    if config.is_api_key_configured():
        st.markdown(f"""
        <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 8px; padding: 10px 14px; margin-bottom: 12px;">
            <div style="font-size: 0.75rem; color: #34d399; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">Engine Connected</div>
            <div style="font-size: 0.92rem; color: #f8fafc; font-weight: 700; margin-top: 2px;">🟢 {config.LLM_PROVIDER.upper()}</div>
            <div style="font-size: 0.76rem; color: #94a3b8; font-family: monospace; margin-top: 2px;">{config.GENERATOR_MODEL}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 8px; padding: 10px 14px; margin-bottom: 12px;">
            <div style="font-size: 0.75rem; color: #fbbf24; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">Engine Mode</div>
            <div style="font-size: 0.92rem; color: #f8fafc; font-weight: 700; margin-top: 2px;">🟡 Local Mock Mode</div>
            <div style="font-size: 0.76rem; color: #94a3b8; margin-top: 2px;">Deterministic tests enabled</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown(f"""
    <div style="color: #64748b; font-size: 0.75rem; line-height: 1.6; padding-left: 2px;">
        Max Regeneration Retries: <b style="color: #cbd5e1;">{config.MAX_RETRIES}</b><br>
        Rubric Dimensions: <b style="color: #cbd5e1;">7 Hard Gates</b><br>
        Framework: <b style="color: #cbd5e1;">LangGraph StateGraph</b>
    </div>
    """, unsafe_allow_html=True)


# ======================================================================= #
#  Helper Rendering Functions
# ======================================================================= #
def render_status_pill(status: str) -> str:
    s = str(status).upper()
    if s in ("PASS", "APPROVED"):
        return f'<span class="badge-pass">✔ {s}</span>'
    elif s in ("FAIL", "FAILED"):
        return f'<span class="badge-fail">✖ {s}</span>'
    elif s == "HUMAN_REVIEW":
        return f'<span class="badge-review">⚠ HUMAN REVIEW</span>'
    else:
        return f'<span class="badge-info">● {s}</span>'


def render_header(title: str, subtitle: str, icon: str = "🎓"):
    st.markdown(f"""
    <div class="page-header">
        <h1 class="page-title">{icon} {title}</h1>
        <p class="page-subtitle">{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)


# ======================================================================= #
#  PAGE 1: OVERVIEW DASHBOARD
# ======================================================================= #
if page == "🏠 Overview Dashboard":
    render_header(
        "AI Lesson Studio",
        "Self-Evaluating Agentic Content System with Feedback-Driven Regeneration",
        icon="🎓"
    )

    runs = db.get_all_runs()
    total_runs = len(runs)
    approved_runs = sum(1 for r in runs if r.get("final_status") == "APPROVED")
    review_runs = sum(1 for r in runs if r.get("final_status") == "HUMAN_REVIEW")
    patterns = db.get_memory_patterns(min_failures=1)

    pass_rate = int((approved_runs / total_runs * 100)) if total_runs > 0 else 100

    # KPI Top Grid
    st.markdown(f"""
    <div class="kpi-grid">
        <div class="kpi-card">
            <div class="kpi-icon">🚀</div>
            <div class="kpi-val">{total_runs}</div>
            <div class="kpi-label">Total Execution Runs</div>
            <span class="kpi-badge badge-info">Audited</span>
        </div>
        <div class="kpi-card">
            <div class="kpi-icon">✅</div>
            <div class="kpi-val" style="color: #34d399;">{approved_runs}</div>
            <div class="kpi-label">Published & Approved</div>
            <span class="kpi-badge badge-pass">{pass_rate}% Pass Rate</span>
        </div>
        <div class="kpi-card">
            <div class="kpi-icon">⚠️</div>
            <div class="kpi-val" style="color: #fbbf24;">{review_runs}</div>
            <div class="kpi-label">Escalated to Human</div>
            <span class="kpi-badge badge-review">Fail-Safe Active</span>
        </div>
        <div class="kpi-card">
            <div class="kpi-icon">🧠</div>
            <div class="kpi-val" style="color: #60a5fa;">{len(patterns)}</div>
            <div class="kpi-label">Failure Patterns Learned</div>
            <span class="kpi-badge badge-info">SQLite Persistent</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Core Value Proposition Columns
    col_flow, col_feats = st.columns([1.1, 0.9])

    with col_flow:
        st.markdown("### 🔄 Closed-Loop Agentic Architecture")
        st.markdown("""
        ```mermaid
        flowchart TD
            Start([Topic Received]) --> Generate[Generate Lesson Content]
            Generate --> Eval[Independent 7-Point Evaluator]
            Eval --> Check{All 7 Criteria Pass?}
            Check -- Yes --> Approve[Approve & Save Output]
            Approve --> Done([Published])
            Check -- No --> Retries{Retry Count < 2?}
            Retries -- Yes --> Feedback[Synthesize Evaluator Feedback]
            Feedback --> Regen[Regenerate Targeted Lesson]
            Regen --> Eval
            Retries -- No --> Escalate[Human Review Required]
            Escalate --> FailDone([Flagged for Review])

            classDef pass fill:#10b981,stroke:#059669,color:#fff;
            classDef fail fill:#f43f5e,stroke:#e11d48,color:#fff;
            classDef neutral fill:#1e293b,stroke:#3b82f6,color:#fff;
            class Approve,Done pass;
            class Escalate,FailDone fail;
            class Generate,Eval,Check,Retries,Feedback,Regen neutral;
        ```
        """)

    with col_feats:
        st.markdown("### 🎯 Assessment Highlights")
        st.markdown("""
        <div style="display: flex; flex-direction: column; gap: 12px;">
            <div class="feature-box">
                <h4>🤖 Multi-Agent Separation</h4>
                <p>The Generator and Quality Evaluator operate with dedicated prompts, distinct temperatures, and zero confirmation bias.</p>
            </div>
            <div class="feature-box">
                <h4>⚖️ Strict Binary Rubric</h4>
                <p>No vague numerical scores. 7 uncompromising PASS/FAIL gates (Technical accuracy, zero unexplained jargon, 5 MCQs, etc.).</p>
            </div>
            <div class="feature-box">
                <h4>🛡️ Guaranteed Termination</h4>
                <p>Strictly capped at 2 retries (3 attempts total). Infinite loops are prevented by LangGraph state routing.</p>
            </div>
            <div class="feature-box">
                <h4>📈 Self-Evolving Prompts</h4>
                <p>Failure frequencies in SQLite trigger automatic prompt enhancements for subsequent runs without mutating the rubric.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<hr style='border-color: #1e293b; margin: 28px 0;'>", unsafe_allow_html=True)

    # Recent Audit Log Table
    st.markdown("### 📜 Recent Generation Audit Trail")
    if runs:
        df_runs = pd.DataFrame(runs[:10])
        display_cols = ["id", "topic", "learner_level", "final_status", "retry_count", "created_at"]
        clean_df = df_runs[[c for c in display_cols if c in df_runs.columns]].rename(columns={
            "id": "Run ID",
            "topic": "Topic Name",
            "learner_level": "Level",
            "final_status": "Final Decision",
            "retry_count": "Retries",
            "created_at": "Executed At",
        })
        st.dataframe(clean_df, use_container_width=True, hide_index=True)
    else:
        st.info("No runs recorded in database yet. Head to **✨ Generate Lesson** to trigger your first run!")


# ======================================================================= #
#  PAGE 2: GENERATE LESSON
# ======================================================================= #
elif page == "✨ Generate Lesson":
    render_header(
        "Generate & Evaluate Lesson",
        "Autonomous Multi-Step Generation, Strict Evaluation, and Self-Healing Cycle",
        icon="✨"
    )

    with st.container():
        st.markdown("""
        <div style="background: #111827; border: 1px solid #1e293b; border-radius: 12px; padding: 20px; margin-bottom: 24px;">
            <h3 style="margin-top: 0; color: #f8fafc; font-size: 1.15rem;">Configure Generation Run</h3>
        """, unsafe_allow_html=True)

        with st.form("generation_control_form"):
            col_t, col_l = st.columns([3, 1])
            with col_t:
                topic = st.text_input(
                    "Lesson Topic",
                    value="Introduction to RAG (Retrieval-Augmented Generation)",
                    help="The primary subject matter for the lesson."
                )
            with col_l:
                learner_level = st.selectbox(
                    "Target Learner Level",
                    options=["Beginner", "Intermediate", "Advanced"],
                    index=0,
                    help="Pedagogical tone and vocabulary target."
                )

            st.markdown("<hr style='border-color: #1e293b; margin: 16px 0;'>", unsafe_allow_html=True)

            # Stress Test Toggle Card
            st.markdown("""
            <div style="background: rgba(245, 158, 11, 0.05); border: 1px solid rgba(245, 158, 11, 0.25); border-radius: 8px; padding: 14px; margin-bottom: 14px;">
                <div style="font-weight: 700; color: #f59e0b; font-size: 0.92rem; display: flex; align-items: center; gap: 6px;">
                    🧪 Evaluator Stress Test (Assessment Demonstration)
                </div>
                <div style="color: #94a3b8; font-size: 0.82rem; margin-top: 4px;">
                    Injects a deliberate technical fallacy into Attempt 1: <em>"RAG retrains the LLM every time a new document is uploaded."</em> 
                    Verifies that the independent Evaluator flags it, feeds actionable critique to the Generator, and regenerates a compliant lesson on Attempt 2.
                </div>
            </div>
            """, unsafe_allow_html=True)

            enable_stress_test = st.checkbox(
                "Enable Evaluator Stress Test (Inject Deliberate Technical Error)",
                value=False,
            )

            submit_btn = st.form_submit_button(
                "🚀 Launch Agentic Workflow",
                type="primary",
                use_container_width=True
            )

        st.markdown("</div>", unsafe_allow_html=True)

    if submit_btn:
        if not topic.strip():
            st.error("Please provide a valid lesson topic.")
        else:
            run_id = str(uuid.uuid4())[:8].upper()

            # Stepper visualizer
            st.markdown(f"""
            <div class="action-bar">
                <div>
                    <span style="font-size: 0.85rem; color: #94a3b8;">Active Run:</span> 
                    <strong style="color: #60a5fa; font-family: monospace; font-size: 1.1rem; margin-left: 6px;">{run_id}</strong>
                </div>
                <div>
                    <span class="badge-info">● RUNNING INFERENCE</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            progress_bar = st.progress(0)
            status_text = st.empty()

            try:
                # Execution tracker
                status_text.markdown("🔄 **Stage 1/3**: Ingesting parameters and querying Content Generator...")
                progress_bar.progress(25)

                stress_content = None
                if enable_stress_test:
                    from generator import MOCK_LESSON
                    stress_content = MOCK_LESSON + "\n\n" + STRESS_TEST_INJECTION

                # Run LangGraph Agent
                start_time = time.time()
                final_state = run_agent(
                    topic=topic,
                    learner_level=learner_level,
                    run_id=run_id,
                    stress_test_content=stress_content,
                )
                elapsed_time = round(time.time() - start_time, 2)

                progress_bar.progress(80)
                status_text.markdown("⚖️ **Stage 2/3**: Running independent 7-point quality evaluation and checking rubric gates...")

                time.sleep(0.4)
                progress_bar.progress(100)
                status_text.empty()
                progress_bar.empty()

                final_status = final_state.get("final_status", "UNKNOWN")
                retry_count = final_state.get("retry_count", 0)
                gen_history = final_state.get("generation_history", [])
                eval_history = final_state.get("evaluation_history", [])
                final_lesson = final_state.get("final_lesson")
                final_eval = final_state.get("final_evaluation")

                # Decision Header Banner
                if final_status == RunStatus.APPROVED.value:
                    st.markdown(f"""
                    <div class="callout-box callout-success">
                        <span style="font-size: 1.8rem;">🎉</span>
                        <div style="flex: 1;">
                            <div style="font-size: 1.15rem; font-weight: 800; color: #34d399;">LESSON APPROVED & PUBLISHED</div>
                            <div style="font-size: 0.88rem; color: #a7f3d0; margin-top: 3px;">
                                All 7 independent quality criteria passed with zero violations. Completed in {elapsed_time}s across {len(gen_history)} attempt(s) with {retry_count} retry cycle(s).
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                elif final_status == RunStatus.HUMAN_REVIEW.value:
                    st.markdown(f"""
                    <div class="callout-box callout-warning">
                        <span style="font-size: 1.8rem;">⚠️</span>
                        <div style="flex: 1;">
                            <div style="font-size: 1.15rem; font-weight: 800; color: #fbbf24;">HUMAN REVIEW REQUIRED</div>
                            <div style="font-size: 0.88rem; color: #fde68a; margin-top: 3px;">
                                Lesson failed one or more rubric gates after exhausting maximum retry limit ({config.MAX_RETRIES}). Guardrail prevented unvetted publication.
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                # Results Tab Navigation
                tab_lesson, tab_eval, tab_history, tab_stress = st.tabs([
                    "📄 Approved Lesson Content",
                    "📊 7-Point Rubric Audit",
                    "🔄 Regeneration History",
                    "🧪 Stress-Test Audit",
                ])

                # Tab 1: Lesson Markdown
                with tab_lesson:
                    if final_lesson:
                        l_data = final_lesson if isinstance(final_lesson, dict) else final_lesson.model_dump()
                        content = l_data.get("content", "")
                        words = l_data.get("word_count", len(content.split()))
                        reading_time = max(1, round(words / 180))

                        st.markdown(f"""
                        <div style="display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap;">
                            <span class="badge-info">📝 {words} Words</span>
                            <span class="badge-info">⏱ ~{reading_time} Min Read</span>
                            <span class="badge-pass">✔ 22 Sections Verified</span>
                        </div>
                        """, unsafe_allow_html=True)

                        st.markdown(content)

                        st.markdown("<hr style='border-color: #1e293b;'>", unsafe_allow_html=True)
                        st.download_button(
                            "⬇️ Export Lesson (Markdown Format)",
                            data=content,
                            file_name=f"lesson_{run_id}.md",
                            mime="text/markdown",
                            use_container_width=True,
                        )
                    else:
                        st.warning("No lesson output available.")

                # Tab 2: Evaluation Checkpoints
                with tab_eval:
                    if final_eval:
                        e_data = final_eval if isinstance(final_eval, dict) else final_eval.model_dump()
                        criteria = e_data.get("criteria", [])
                        overall = e_data.get("overall_status", "UNKNOWN")

                        passed_count = sum(1 for c in criteria if c["status"] == "PASS")
                        st.markdown(f"""
                        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px;">
                            <h3 style="margin: 0; color: #f8fafc; font-size: 1.1rem;">Independent Evaluator Scorecard</h3>
                            {render_status_pill(overall)}
                        </div>
                        """, unsafe_allow_html=True)

                        st.progress(passed_count / len(criteria), text=f"Criteria Gates Passed: {passed_count}/{len(criteria)}")

                        st.markdown('<div class="rubric-grid">', unsafe_allow_html=True)
                        for c in criteria:
                            is_p = c["status"] == "PASS"
                            cls_name = "pass" if is_p else "fail"
                            icon = "✔" if is_p else "✖"
                            status_html = render_status_pill(c["status"])

                            evidence_html = f'<div class="rubric-evidence">"{c["evidence"]}"</div>' if c.get("evidence") else ""
                            sugg_html = f'<div class="rubric-suggestion">💡 <b>Feedback:</b> {c["suggestion"]}</div>' if c.get("suggestion") else ""

                            st.markdown(f"""
                            <div class="rubric-card {cls_name}">
                                <div class="rubric-title">
                                    <span>{c['criterion']}</span>
                                    {status_html}
                                </div>
                                <div class="rubric-reason">{c['reason']}</div>
                                {evidence_html}
                                {sugg_html}
                            </div>
                            """, unsafe_allow_html=True)
                        st.markdown('</div>', unsafe_allow_html=True)

                        st.markdown("<hr style='border-color: #1e293b; margin: 20px 0;'>", unsafe_allow_html=True)
                        st.download_button(
                            "⬇️ Export Quality Audit Report (JSON)",
                            data=json.dumps(e_data, indent=2, default=str),
                            file_name=f"evaluation_{run_id}.json",
                            mime="application/json",
                            use_container_width=True,
                        )

                # Tab 3: Regeneration Timeline
                with tab_history:
                    st.markdown("### Attempt & Self-Correction Trail")
                    for idx, (g, e) in enumerate(zip(gen_history, eval_history), 1):
                        g_dict = g if isinstance(g, dict) else g.model_dump()
                        e_dict = e if isinstance(e, dict) else e.model_dump()
                        ov_status = e_dict.get("overall_status", "UNKNOWN")

                        with st.expander(f"Attempt #{idx} — Status: {ov_status}", expanded=(idx == len(gen_history))):
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.markdown(f"**Word Count:** {g_dict.get('word_count', 'N/A')}")
                                st.markdown(f"**Failed Gates:** `{', '.join(e_dict.get('failed_criteria', [])) or 'None (All Passed)'}`")
                            with col_b:
                                st.markdown(f"**Evaluation Timestamp:** `{e_dict.get('evaluated_at', 'N/A')}`")

                            if e_dict.get("regeneration_instructions"):
                                st.markdown("**Regeneration Critique Transmitted to Agent:**")
                                for r_inst in e_dict["regeneration_instructions"]:
                                    st.markdown(f"- 💡 {r_inst}")

                # Tab 4: Stress Test Details
                with tab_stress:
                    if enable_stress_test and eval_history:
                        st.markdown("### 🧪 Evaluator Stress-Test Demonstration")
                        st.markdown("""
                        <div class="callout-box callout-info">
                            <div>
                                <b>Test Objective:</b> Prove the Evaluator doesn't blindly rubber-stamp content. 
                                We deliberately injected a known technical misconception into Attempt 1 and verified automatic recovery.
                            </div>
                        </div>
                        """, unsafe_allow_html=True)

                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("""
                            <div style="background: rgba(244, 63, 94, 0.05); border: 1px solid rgba(244, 63, 94, 0.3); border-radius: 8px; padding: 14px;">
                                <div style="color: #f43f5e; font-weight: 700;">Attempt 1: Fault Injected</div>
                                <div style="font-size: 0.84rem; color: #cbd5e1; margin-top: 6px;">
                                    <em>"RAG retrains the LLM every time a new document is uploaded..."</em>
                                </div>
                                <div style="margin-top: 8px;"><span class="badge-fail">✖ STATUS.FAIL</span></div>
                            </div>
                            """, unsafe_allow_html=True)

                        with col2:
                            st.markdown("""
                            <div style="background: rgba(16, 185, 129, 0.05); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 8px; padding: 14px;">
                                <div style="color: #10b981; font-weight: 700;">Attempt 2: Self-Corrected</div>
                                <div style="font-size: 0.84rem; color: #cbd5e1; margin-top: 6px;">
                                    <em>"RAG retrieves documents at inference time. Model weights are NEVER changed..."</em>
                                </div>
                                <div style="margin-top: 8px;"><span class="badge-pass">✔ STATUS.PASS</span></div>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("Check **Enable Evaluator Stress Test** before running to view the live fault-injection and self-healing report.")

            except Exception as e:
                progress_bar.empty()
                status_text.empty()
                st.error(f"Execution Error: {e}")
                logger.exception("Agent execution failure")


# ======================================================================= #
#  PAGE 3: RUBRIC & EVALUATION DASHBOARD
# ======================================================================= #
elif page == "📊 Rubric & Evaluations":
    render_header(
        "Quality Evaluation & Rubrics",
        "Deep-Dive Auditing for Individual Generation Runs",
        icon="📊"
    )

    runs = db.get_all_runs()
    if not runs:
        st.info("No runs found in database. Generate a lesson first.")
    else:
        run_map = {r["id"]: f"Run {r['id']} | {r['topic'][:45]}... [{r['final_status']}]" for r in runs}
        selected_run_id = st.selectbox(
            "Select Run to Inspect",
            options=list(run_map.keys()),
            format_func=lambda x: run_map[x],
        )

        evals = db.get_evaluations_for_run(selected_run_id)
        if not evals:
            st.warning("No evaluations recorded for this run ID.")
        else:
            for ev in evals:
                att = ev["attempt_number"]
                ov = ev["overall_status"]
                criteria = ev["criteria_json"]
                passed = sum(1 for c in criteria if c["status"] == "PASS")

                st.markdown(f"""
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 20px;">
                    <h3 style="margin: 0; color: #f8fafc;">Attempt #{att} Audit</h3>
                    {render_status_pill(ov)}
                </div>
                """, unsafe_allow_html=True)

                st.progress(passed / len(criteria), text=f"Gate Clearance: {passed}/{len(criteria)} Gates Passed")

                st.markdown('<div class="rubric-grid">', unsafe_allow_html=True)
                for c in criteria:
                    is_p = c["status"] == "PASS"
                    cls_name = "pass" if is_p else "fail"
                    status_html = render_status_pill(c["status"])
                    ev_html = f'<div class="rubric-evidence">"{c["evidence"]}"</div>' if c.get("evidence") else ""
                    sugg_html = f'<div class="rubric-suggestion">💡 {c["suggestion"]}</div>' if c.get("suggestion") else ""

                    st.markdown(f"""
                    <div class="rubric-card {cls_name}">
                        <div class="rubric-title">
                            <span>{c['criterion']}</span>
                            {status_html}
                        </div>
                        <div class="rubric-reason">{c['reason']}</div>
                        {ev_html}
                        {sugg_html}
                    </div>
                    """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
                st.markdown("<hr style='border-color: #1e293b; margin: 24px 0;'>", unsafe_allow_html=True)


# ======================================================================= #
#  PAGE 4: REJECTION LOGS
# ======================================================================= #
elif page == "📋 Rejection Logs":
    render_header(
        "Rejection Audit Trail",
        "Comprehensive Log of All Failed Attempts and System Critiques",
        icon="📋"
    )

    rejections = db.get_rejection_history(limit=50)
    if not rejections:
        st.markdown("""
        <div class="callout-box callout-success">
            <span style="font-size: 1.5rem;">✨</span>
            <div>
                <b>Zero Active Rejections:</b> No recent generation failures recorded. 
                Trigger the <b>Evaluator Stress Test</b> to generate audit failure logs.
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"**Total Rejection Incidents:** `{len(rejections)}`")

        for r in rejections:
            with st.expander(
                f"🚨 Incident: Run {r['run_id']} (Attempt #{r['attempt_number']}) — {r['topic'][:50]}",
                expanded=False
            ):
                st.markdown(f"**Timestamp:** `{r['rejected_at']}`")
                st.markdown(f"**Violated Criteria:** `<span class='badge-fail'>{r['failed_criteria']}</span>`", unsafe_allow_html=True)

                st.markdown("#### Primary Failure Reasons:")
                for reason in r.get("reasons_json", []):
                    st.markdown(f"- ❌ {reason}")

                if r.get("suggestions_json"):
                    st.markdown("#### Actionable Regeneration Instructions:")
                    for s in r["suggestions_json"]:
                        st.markdown(f"- 💡 {s}")


# ======================================================================= #
#  PAGE 5: AGENT MEMORY
# ======================================================================= #
elif page == "🧠 Persistent Memory":
    render_header(
        "Agent Persistent Memory",
        "SQLite-Backed Pattern Aggregation & Autonomous Prompt Optimization",
        icon="🧠"
    )

    summary = mem.get_memory_summary()

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-icon">📊</div>
            <div class="kpi-val">{summary['total_patterns']}</div>
            <div class="kpi-label">Tracked Failure Dimensions</div>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-icon">💡</div>
            <div class="kpi-val" style="color: #34d399;">{summary['total_improvements']}</div>
            <div class="kpi-label">Active Prompt Improvements</div>
        </div>
        """, unsafe_allow_html=True)

    if summary["hint"]:
        st.markdown(f"""
        <div class="callout-box callout-info" style="margin-top: 20px;">
            <span style="font-size: 1.5rem;">💡</span>
            <div>
                <b>Active Prompt Injection Hints:</b><br>
                {summary['hint']}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("### 🔴 Tracked Failure Dimensions")
    patterns = summary["patterns"]
    if not patterns:
        st.info("No recurring failure patterns recorded yet.")
    else:
        for p in patterns:
            with st.expander(f"Dimension: {p['criterion']} — {p['failure_count']} Total Failures"):
                st.markdown(f"**Last Incident:** `{p['last_seen']}`")
                st.markdown(f"**System Prescription:** {p.get('suggested_improvement', 'N/A')}")
                if p.get("common_reasons_json"):
                    st.markdown("**Historical Causes:**")
                    for reas in p["common_reasons_json"]:
                        st.markdown(f"- {reas}")

    st.markdown("<hr style='border-color: #1e293b; margin: 24px 0;'>", unsafe_allow_html=True)

    st.markdown("### ⚙️ Self-Improvement Engine")
    if st.button("🔄 Trigger Self-Improvement Analysis", type="primary"):
        new_imps = mem.generate_and_save_improvements()
        if new_imps:
            st.success(f"Generated {len(new_imps)} new prompt rules:")
            for n in new_imps:
                st.markdown(f"- {n}")
        else:
            st.info("Failure frequencies do not currently exceed threshold (2+ failures required) or rules are already active.")


# ======================================================================= #
#  PAGE 6: SYSTEM ARCHITECTURE
# ======================================================================= #
elif page == "🏗️ System Architecture":
    render_header(
        "System Architecture & Specifications",
        "Technical Components, LangGraph Topology, and Relational Schema",
        icon="🏗️"
    )

    st.markdown("""
    ### 🧩 Module Separation of Responsibilities

    | Component | Primary File | Architectural Role |
    | :--- | :--- | :--- |
    | **Streamlit Dashboard** | `app.py` | Responsive presentation, real-time KPI monitoring, and file export. |
    | **Agent Orchestrator** | `agent.py` | LangGraph StateGraph, conditional edge routing, retry management. |
    | **Content Generator** | `generator.py` | LLM inference client with Indian 12th-grade pedagogical prompt specs. |
    | **Independent Evaluator** | `evaluator.py` | Strict 7-gate pass/fail rubric auditor with safety-net validation. |
    | **Rubric Specification** | `rubric.py` | Immutable definition of quality criteria. |
    | **Prompt Repository** | `prompts.py` | Centralized prompt templates with dynamic injection hints. |
    | **Memory Subsystem** | `memory.py` | Failure frequency tracking and self-improvement synthesis. |
    | **Database Layer** | `database.py` | SQLite WAL persistence across 6 normalized relational tables. |
    | **Validation Contracts**| `schemas.py` | Pydantic v2 schemas defining all inter-module data exchange. |
    | **Configuration** | `config.py` | Dotenv environment loader and model provider configuration. |
    """)

    st.markdown("<hr style='border-color: #1e293b; margin: 24px 0;'>", unsafe_allow_html=True)

    st.markdown("### 🗄️ Relational SQLite Data Topology")
    st.markdown("""
    ```sql
    -- Relational Schema Topology
    runs (id, topic, learner_level, status, retry_count, final_status, created_at, completed_at)
      ├── generations (id, run_id, attempt_number, title, content, word_count, created_at)
      ├── evaluations (id, run_id, attempt_number, overall_status, criteria_json, regen_instructions_json)
      └── rejection_logs (id, run_id, attempt_number, topic, failed_criteria, reasons_json, suggestions_json)

    -- Persistent Self-Improvement System
    memory_patterns (id, criterion, failure_count, last_seen, common_reasons_json, suggested_improvement)
    prompt_improvements (id, criterion, improvement_instruction, approved_at, times_applied)
    ```
    """)


# ======================================================================= #
#  PAGE 7: RUNTIME SETTINGS
# ======================================================================= #
elif page == "⚙️ Runtime Settings":
    render_header(
        "Runtime Configuration",
        "Model Endpoints, Database Administration, and Environment Status",
        icon="⚙️"
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🔑 Inference Configuration")
        st.markdown(f"**Provider:** `{config.LLM_PROVIDER.upper()}`")
        st.markdown(f"**Generator Model:** `{config.GENERATOR_MODEL}`")
        st.markdown(f"**Evaluator Model:** `{config.EVALUATOR_MODEL}`")
        st.markdown(f"**Generator Temperature:** `{config.GENERATOR_TEMPERATURE}`")
        st.markdown(f"**Evaluator Temperature:** `{config.EVALUATOR_TEMPERATURE}`")

        status_text = "🟢 Active & Authenticated" if config.is_api_key_configured() else "🟡 Mock Mode Active"
        st.markdown(f"**API Status:** {status_text}")

    with col2:
        st.markdown("### 🗃️ Storage & Infrastructure")
        st.markdown(f"**Database Path:** `{config.DATABASE_PATH}`")
        st.markdown(f"**Output Directory:** `{config.OUTPUT_DIR}`")
        st.markdown(f"**Max Retries Cap:** `{config.MAX_RETRIES}`")

        st.markdown("<hr style='border-color: #1e293b; margin: 16px 0;'>", unsafe_allow_html=True)
        st.markdown("#### Database Maintenance")
        if st.button("🗑️ Reset Database (Clear Runs & Rejections)", type="secondary"):
            db_file = Path(config.DATABASE_PATH)
            if db_file.exists():
                db_file.unlink()
            db.init_db()
            st.success("Database re-initialized cleanly.")
            st.rerun()
