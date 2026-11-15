"""
generate_loom_script_pdf.py — Generates an executive, beautifully styled PDF
of the Complete Spoken Loom Video Script for the GenAI Engineer Assessment.
"""

import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    """Adds professional running header and footer with page numbers."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 11 * 72 - 36, "AI Lesson Studio | Spoken Loom Video Script")
            self.drawRightString(8.5 * 72 - 54, 11 * 72 - 36, "GenAI Engineer Assessment - Content Systems")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(54, 11 * 72 - 42, 8.5 * 72 - 54, 11 * 72 - 42)
            
        # Footer
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawString(54, 34, "Confidential - Candidate Walkthrough Script (Thanigaivel Kannan)")
        self.drawRightString(8.5 * 72 - 54, 34, page_str)
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(54, 46, 8.5 * 72 - 54, 46)
        
        self.restoreState()


def build_pdf(filename="Loom_Video_Walkthrough_Script.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()
    
    # Custom Typography Styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=26,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=4,
    )
    
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#3B82F6"),
        spaceAfter=14,
    )
    
    sec_heading_style = ParagraphStyle(
        "SecHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#0F172A"),
        spaceBefore=14,
        spaceAfter=6,
    )
    
    stage_cue_style = ParagraphStyle(
        "StageCue",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#64748B"),
        spaceAfter=6,
    )
    
    spoken_style = ParagraphStyle(
        "SpokenText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=14.5,
        textColor=colors.HexColor("#1E293B"),
        spaceAfter=6,
    )
    
    bullet_style = ParagraphStyle(
        "BulletText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13.5,
        textColor=colors.HexColor("#334155"),
        leftIndent=15,
        spaceAfter=3,
    )
    
    table_cell = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#1E293B"),
    )
    
    table_cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#0F172A"),
    )

    elements = []

    # Title Banner
    elements.append(Paragraph("AI Lesson Studio — Loom Video Script", title_style))
    elements.append(Paragraph("Official Spoken Walkthrough (15–18 Mins) | Candidate: Thanigaivel Kannan", subtitle_style))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#3B82F6"), spaceAfter=14))

    # Executive Overview Box
    meta_data = [
        [
            Paragraph("<b>Role:</b> GenAI Engineer – Content Systems", table_cell),
            Paragraph("<b>Target Audience:</b> 12th-grade Indian student (non-English medium)", table_cell)
        ],
        [
            Paragraph("<b>Submission Topic:</b> Introduction to RAG", table_cell),
            Paragraph("<b>Stack:</b> LangGraph, Streamlit, SQLite, Groq (gpt-oss-20b)", table_cell)
        ],
        [
            Paragraph("<b>Format:</b> Screen + Camera (Face visible required)", table_cell),
            Paragraph("<b>Total Time:</b> 15 to 18 Minutes", table_cell)
        ]
    ]
    t_meta = Table(meta_data, colWidths=[240, 264])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F8FAFC")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E2E8F0")),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(t_meta)
    elements.append(Spacer(1, 14))

    # SECTION 1
    elements.append(Paragraph("Section 1: Introduction & Problem Context [00:00 – 02:00]", sec_heading_style))
    elements.append(Paragraph("<b>[Screen Setup]:</b> Browser open on the <i>Overview Dashboard</i> of AI Lesson Studio (http://localhost:8501). Face visible in Loom corner bubble.", stage_cue_style))
    elements.append(Paragraph(
        "\"Hello everyone, my name is Thanigaivel Kannan. Today, I am excited to present my technical assessment project for the role of <b>GenAI Engineer – Content Systems</b>: <b>AI Lesson Studio</b>.",
        spoken_style
    ))
    elements.append(Paragraph(
        "The objective of this assessment is not simply to write a prompt that generates educational content. The real challenge is building and owning a production-grade, <b>closed-loop agentic system</b> that generates educational material, independently evaluates its own quality against a strict pass/fail rubric, detects technical errors, heals itself through feedback-driven regeneration, maintains persistent memory across runs, and autonomously decides whether content clears the bar before a human ever sees it.",
        spoken_style
    ))
    elements.append(Paragraph(
        "Our target audience is a 12th-grade student from India with limited English vocabulary and no prior AI background. Our topic of submission is <b>Introduction to RAG (Retrieval-Augmented Generation)</b>.\"",
        spoken_style
    ))
    elements.append(Spacer(1, 10))

    # SECTION 2
    elements.append(Paragraph("Section 2: Architecture & LangGraph Design [02:00 – 05:30]", sec_heading_style))
    elements.append(Paragraph("<b>[Action]:</b> In the sidebar, click on <i>'🏗️ System Architecture'</i>. Point cursor to the LangGraph flowchart and module table.", stage_cue_style))
    elements.append(Paragraph(
        "\"Let's take a look at the system architecture. On this screen, you can see our LangGraph workflow and modular structure.",
        spoken_style
    ))
    elements.append(Paragraph("There are several core architectural principles implemented here:", spoken_style))
    elements.append(Paragraph(
        "• <b>Strict Multi-Agent Separation:</b> We have two completely decoupled agents. The <i>Content Generator</i> uses an LLM with a creative temperature of 0.7 to produce beginner-friendly pedagogical lessons. The <i>Quality Evaluator</i> is completely independent. It operates with a deterministic temperature of 0.1 and has zero confirmation bias—it never sees the generator's internal thoughts, only the generated lesson output.",
        bullet_style
    ))
    elements.append(Paragraph(
        "• <b>Binary PASS/FAIL Rubric:</b> We do not use vague numerical scores like 7/10. Either content clears every single one of our 7 rubric gates, or it fails. A single failure triggers regeneration.",
        bullet_style
    ))
    elements.append(Paragraph(
        "• <b>Guaranteed Termination & Human Escalation:</b> The LangGraph state graph enforces <code>MAX_RETRIES = 2</code>. If a lesson fails twice, it routes to a <code>human_review_node</code>, setting the status to 'HUMAN REVIEW REQUIRED' rather than entering an infinite loop or falsely approving bad content.",
        bullet_style
    ))
    elements.append(Paragraph(
        "• <b>Persistent SQLite Database:</b> We persist all runs, generation attempts, evaluation JSONs, rejection logs, and learned memory patterns across application restarts using SQLite with WAL mode.\"",
        bullet_style
    ))
    elements.append(Spacer(1, 10))

    # SECTION 3
    elements.append(Paragraph("Section 3: Live Demo — Normal Generation Flow [05:30 – 09:00]", sec_heading_style))
    elements.append(Paragraph("<b>[Action]:</b> Click <i>'✨ Generate Lesson'</i>. Keep default topic and click <i>'🚀 Launch Agentic Workflow'</i>.", stage_cue_style))
    elements.append(Paragraph(
        "\"Now let's demonstrate the application live. Here on the <b>Generate Lesson</b> page, we enter our topic: 'Introduction to RAG (Retrieval-Augmented Generation)' with Learner Level set to 'Beginner'.",
        spoken_style
    ))
    elements.append(Paragraph(
        "<i>(Click button)</i> Notice our multi-stage progress pipeline. In Stage 1, the LangGraph agent calls the Generator, fetching historical failure hints from persistent memory. In Stage 2, the independent Evaluator inspects all 7 dimensions.",
        spoken_style
    ))
    elements.append(Paragraph(
        "The result is in: <b>LESSON APPROVED & PUBLISHED</b> on Attempt #1 with 0 retries used.",
        spoken_style
    ))
    elements.append(Paragraph(
        "Let's inspect the <b>Approved Lesson Content</b> tab:<br/>"
        "• Notice how the lesson is tailored for Indian 12th-grade students: it uses relatable everyday analogies like Google Search, WhatsApp messaging, YouTube recommendations, and university library rules.<br/>"
        "• It explains all 22 required sections: Document loading, chunking, embeddings, vector databases, prompt augmentation, retrieval, generation, a complete comparison table, common beginner mistakes, a structured glossary, and exactly 5 MCQs with explanations.<br/>"
        "• Notice the download button at the bottom where teachers or students can export the full lesson in Markdown.<br/>"
        "• Switching to the <b>Rubric Audit tab</b>, all 7 gates—Technical Accuracy, Beginner Language, Practical Examples, Jargon Explanation, Key Topic Coverage, Teaching Flow, and Knowledge Assessment—cleared with direct excerpt evidence.\"",
        spoken_style
    ))
    elements.append(Spacer(1, 10))

    # SECTION 4
    elements.append(Paragraph("Section 4: The Core Stress Test — Error Injection & Self-Healing [09:00 – 13:00]", sec_heading_style))
    elements.append(Paragraph("<b>[Action]:</b> Check <i>'Enable Evaluator Stress Test'</i>. Click <i>'🚀 Launch Agentic Workflow'</i>.", stage_cue_style))
    elements.append(Paragraph(
        "\"Now let's demonstrate the most critical capability required by the assessment: the <b>Evaluator Stress Test</b>.",
        spoken_style
    ))
    elements.append(Paragraph(
        "A common problem with naïve evaluators is that they blindly rubber-stamp whatever the LLM writes. To prove our evaluator is genuinely rigorous and independent, we inject a known technical fallacy into Attempt 1:<br/>"
        "<i>'RAG retrains the underlying LLM every time a new document is uploaded.'</i><br/>"
        "This is factually false. RAG retrieves documents at inference time; it never modifies model weights.",
        spoken_style
    ))
    elements.append(Paragraph(
        "<i>(Wait for run to complete, then open the Stress-Test tab)</i><br/>"
        "Let's look at what happened:<br/>"
        "1. On <b>Attempt 1</b>, the evaluator caught the error immediately. <code>Technical Accuracy</code> was marked as <b>STATUS.FAIL</b>.<br/>"
        "2. The evaluator logged the critique: <i>'The lesson contains an incorrect statement that RAG retrains the LLM each time a new document is added...'</i><br/>"
        "3. Actionable feedback was compiled: <i>'Remove the false claim. Clearly state that RAG operates at inference time and model weights are never changed.'</i><br/>"
        "4. The LangGraph conditional edge saw that <code>retry_count < 2</code>, routed to the feedback node, and triggered Attempt 2.<br/>"
        "5. On <b>Attempt 2</b>, the generator consumed the critique, corrected the explanation, and the evaluator approved the corrected lesson as <b>STATUS.PASS</b>!<br/>"
        "6. In the <b>Rejection Logs</b> in the sidebar, we see the full audit trail: the exact timestamp, the violated criteria, the reason, and the remediation instructions.\"",
        spoken_style
    ))
    elements.append(Spacer(1, 10))

    # SECTION 5
    elements.append(Paragraph("Section 5: Persistent Memory & Self-Improvement [13:00 – 15:00]", sec_heading_style))
    elements.append(Paragraph("<b>[Action]:</b> Click <i>'🧠 Persistent Memory'</i> in the sidebar.", stage_cue_style))
    elements.append(Paragraph(
        "\"Next, let's explore <b>Persistent Memory and Self-Improvement</b>.<br/>"
        "Our system doesn't forget failures when the app restarts. Every failed gate is tracked in the SQLite <code>memory_patterns</code> table.<br/>"
        "Here on the dashboard, we see that <code>Technical Accuracy</code> has a failure count tracked. When a dimension fails repeatedly, the system automatically synthesizes an approved prompt improvement rule that gets injected into all future generator prompts.<br/>"
        "Notice that while generator instructions self-improve, <b>the evaluator rubric remains strictly immutable</b>. The generator is never allowed to lower the evaluator's standards.\"",
        spoken_style
    ))
    elements.append(Spacer(1, 10))

    # SECTION 6
    elements.append(Paragraph("Section 6: Automated Testing & Deliverables Summary [15:00 – 17:30]", sec_heading_style))
    elements.append(Paragraph("<b>[Action]:</b> Switch to Terminal. Run <code>python -m pytest tests/ -v</code>. Then open GitHub Repo and Google Doc.", stage_cue_style))
    elements.append(Paragraph(
        "\"Finally, let's look at the testing suite and deliverables.<br/>"
        "<i>(Show terminal running pytest)</i><br/>"
        "As you can see, we have <b>69 comprehensive unit and integration tests</b> covering the generator, evaluator, LangGraph edge routing, maximum retry enforcement, SQLite persistence, and automated stress testing. All 69 tests pass with zero external API dependencies in mock mode.<br/>"
        "To summarize our submission deliverables:<br/>"
        "1. Our GitHub repository at <code>github.com/Thanigaivelk-official/rag-lesson-generator</code> is public and includes all code, documentation, architecture diagrams, and setup instructions.<br/>"
        "2. Our approved lesson content is published on Google Docs with public view access.<br/>"
        "3. And this Loom video demonstrates our full agentic closed-loop in action.<br/>"
        "Thank you very much for your time and consideration.\"",
        spoken_style
    ))
    elements.append(Spacer(1, 14))

    # Checklist Table at the end
    elements.append(Paragraph("Candidate Quick Checklist Before Recording", sec_heading_style))
    checklist_data = [
        [Paragraph("<b>Step</b>", table_cell_bold), Paragraph("<b>Verification Item</b>", table_cell_bold), Paragraph("<b>Status</b>", table_cell_bold)],
        [Paragraph("1", table_cell), Paragraph("Loom settings: Screen + Camera (Face visible in corner bubble)", table_cell), Paragraph("Mandatory", table_cell_bold)],
        [Paragraph("2", table_cell), Paragraph("Streamlit app running at http://localhost:8501", table_cell), Paragraph("Ready", table_cell)],
        [Paragraph("3", table_cell), Paragraph("Normal flow demonstrated: Attempt 1 PASS (7/7 criteria)", table_cell), Paragraph("Ready", table_cell)],
        [Paragraph("4", table_cell), Paragraph("Stress test demonstrated: Attempt 1 FAIL -> Feedback -> Attempt 2 PASS", table_cell), Paragraph("Ready", table_cell)],
        [Paragraph("5", table_cell), Paragraph("Terminal test suite shown: 69/69 Pytest tests passing", table_cell), Paragraph("Ready", table_cell)],
        [Paragraph("6", table_cell), Paragraph("GitHub repo & Google Doc links verified public", table_cell), Paragraph("Verified", table_cell)],
    ]
    t_chk = Table(checklist_data, colWidths=[36, 384, 84])
    t_chk.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#0F172A")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor("#F8FAFC"), colors.white]),
        ('TOPPADDING', (0,1), (-1,-1), 4),
        ('BOTTOMPADDING', (0,1), (-1,-1), 4),
    ]))
    elements.append(t_chk)

    # Build PDF
    doc.build(elements, canvasmaker=NumberedCanvas)
    print(f"Successfully generated: {filename}")

if __name__ == "__main__":
    output_path = os.path.join("docs", "Loom_Video_Walkthrough_Script.pdf")
    build_pdf(output_path)
