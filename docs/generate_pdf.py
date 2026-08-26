from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    ListFlowable, ListItem, PageBreak, HRFlowable
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

INK = colors.HexColor("#101A2E")
BRASS = colors.HexColor("#B9832A")
TEAL = colors.HexColor("#2E9E85")
MUTED = colors.HexColor("#555F73")
LINE = colors.HexColor("#D8DEE9")

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="TitleBig", fontName="Helvetica-Bold", fontSize=24, leading=28, textColor=INK, spaceAfter=6))
styles.add(ParagraphStyle(name="Subtitle", fontName="Helvetica", fontSize=13, leading=16, textColor=MUTED, spaceAfter=18))
styles.add(ParagraphStyle(name="H1", fontName="Helvetica-Bold", fontSize=16, leading=20, textColor=INK, spaceBefore=18, spaceAfter=8))
styles.add(ParagraphStyle(name="H2", fontName="Helvetica-Bold", fontSize=12.5, leading=16, textColor=BRASS, spaceBefore=10, spaceAfter=6))
styles.add(ParagraphStyle(name="Body", fontName="Helvetica", fontSize=10, leading=15, textColor=INK, spaceAfter=8, alignment=TA_LEFT))
styles.add(ParagraphStyle(name="BodyBold", parent=styles["Body"], fontName="Helvetica-Bold"))
styles.add(ParagraphStyle(name="Caption", fontName="Helvetica-Oblique", fontSize=8.5, textColor=MUTED))
styles.add(ParagraphStyle(name="MonoBlock", fontName="Courier", fontSize=8, leading=11, textColor=INK, backColor=colors.HexColor("#F4F6FA"), borderPadding=8, spaceAfter=10))

def h1(text): return Paragraph(text, styles["H1"])
def h2(text): return Paragraph(text, styles["H2"])
def body(text): return Paragraph(text, styles["Body"])
def bullets(items):
    return ListFlowable(
        [ListItem(Paragraph(t, styles["Body"]), leftIndent=6) for t in items],
        bulletType="bullet", start="•", leftIndent=16, spaceBefore=2, spaceAfter=10,
    )

def rule():
    return HRFlowable(width="100%", thickness=0.75, color=LINE, spaceBefore=4, spaceAfter=14)

def styled_table(header, rows, col_widths):
    data = [header] + rows
    t = Table(data, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.5, LINE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F9FC")]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
    ]))
    return t

def wrap_cell(text):
    return Paragraph(text, ParagraphStyle(name="cell", fontName="Helvetica", fontSize=8.5, leading=11))

doc = SimpleDocTemplate(
    "/home/claude/learning-path-recommender/docs/Pathfinder_Solution_Documentation.pdf",
    pagesize=LETTER,
    topMargin=0.85 * inch, bottomMargin=0.75 * inch,
    leftMargin=0.8 * inch, rightMargin=0.8 * inch,
    title="Pathfinder — Solution Documentation",
    author="Pathfinder Project",
)

story = []

# ---------- Cover ----------
story.append(Spacer(1, 60))
story.append(Paragraph("PATHFINDER", ParagraphStyle(name="cover1", fontName="Helvetica-Bold", fontSize=34, leading=40, textColor=INK)))
story.append(Spacer(1, 10))
story.append(Paragraph("AI-Powered Personalized Learning Path Recommender", ParagraphStyle(name="cover2", fontName="Helvetica", fontSize=15, leading=19, textColor=BRASS, spaceAfter=30)))
story.append(rule())
story.append(Paragraph("Solution Documentation", styles["H1"]))
story.append(Paragraph(
    "Problem understanding · Solution approach · System architecture · "
    "AI/ML techniques · Key features & workflows · Challenges faced",
    styles["Subtitle"]))
story.append(Spacer(1, 220))
story.append(Paragraph(
    "This document accompanies the Pathfinder source code submission. "
    "See README.md in the repository root for setup &amp; execution instructions.",
    styles["Caption"]))
story.append(PageBreak())

# ---------- 1. Problem Understanding ----------
story.append(h1("1. Problem Understanding"))
story.append(body(
    "Online learning platforms have solved <b>content discovery</b> — thousands of courses, "
    "searchable and tagged — but not <b>sequencing</b>. A learner who knows they want to "
    "\"become a data scientist\" is still left to manually work out which courses are actually "
    "relevant, what order to take them in given their existing knowledge, whether they already "
    "know some of the material, how to prove they've learned it, and what to do when a course "
    "turns out to be too easy, too hard, or their goal shifts."
))
story.append(body(
    "A one-size-fits-all \"top 10 courses\" list ignores the learner's starting point entirely. "
    "The core problem is therefore not recommendation in isolation — it is <b>goal-conditioned "
    "sequencing with continuous adaptation</b>: profile the learner, understand the goal, identify "
    "the skill gap between them, and produce an ordered, explainable, living roadmap."
))

# ---------- 2. Solution Approach ----------
story.append(h1("2. Solution Approach"))
story.append(body("Pathfinder is built around four cooperating engines, each with a single responsibility, orchestrated by a thin REST API layer:"))
story.append(bullets([
    "<b>Learner Profiling Engine</b> — captures interests, free-text goal, experience level, known skills, completed/in-progress courses and a feedback log, built up conversationally rather than through a long intake form.",
    "<b>Recommendation Engine</b> — matches the learner's free-text goal against a course catalog using TF-IDF + cosine similarity, then re-scores candidates against the learner's specific profile: goal relevance, proportion of newly-taught skills, and a level-mismatch penalty.",
    "<b>Learning Path Generator</b> — expands the top-matched courses into their full prerequisite chains (a directed acyclic graph), topologically sorts them, and annotates milestones (projects/assessments) and cumulative time estimates.",
    "<b>Explainability Layer</b> — turns the structured scores/gaps/prerequisite state from the engines above into natural-language explanations and answers to learner questions, strictly grounded in the computed data.",
]))
story.append(body(
    "A learner interacts entirely through natural language in the chat interface; every message "
    "updates the profile and triggers a full path regeneration, so the roadmap is always a live "
    "reflection of the latest known state."
))

# ---------- 3. System Architecture ----------
story.append(h1("3. System Architecture"))
story.append(Paragraph(
    "frontend/ (static, no build step — React + Chart.js via CDN)<br/>"
    "&nbsp;&nbsp;index.html · app.jsx (chat / roadmap / dashboard UI) · styles.css<br/>"
    "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│  REST / JSON (fetch)<br/>"
    "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;▼<br/>"
    "backend/ (FastAPI, Python)<br/>"
    "&nbsp;&nbsp;main.py — API orchestration<br/>"
    "&nbsp;&nbsp;engine/profiling.py — learner profile store<br/>"
    "&nbsp;&nbsp;engine/recommender.py — TF-IDF goal matcher + scoring<br/>"
    "&nbsp;&nbsp;engine/path_generator.py — prerequisite DAG → topological roadmap<br/>"
    "&nbsp;&nbsp;engine/explainer.py — grounded natural-language explanations<br/>"
    "&nbsp;&nbsp;data/courses.json — course catalog (24 items, 6 domains)",
    styles["MonoBlock"]
))
story.append(h2("Data flow — new goal"))
story.append(body(
    "chat message → intake parser (level / skills / interests) → profile update → TF-IDF "
    "goal↔course matching → skill-gap scored ranking → prerequisite expansion → topological "
    "sort → explanation generation → roadmap returned to UI"
))
story.append(h2("Data flow — adaptation"))
story.append(body(
    "mark complete / feedback → profile update (known_skills, completed_ids) → full path "
    "regeneration → UI reflects new roadmap + dashboard stats"
))

story.append(PageBreak())

# ---------- 4. AI/ML Techniques ----------
story.append(h1("4. AI / ML Techniques Used"))
header = ["Technique", "Where", "Why"]
rows = [
    [wrap_cell("TF-IDF vectorization + cosine similarity"), wrap_cell("recommender.py"),
     wrap_cell("Matches free-text goals to the most semantically relevant courses without an external embeddings API — keeps the prototype fully offline and reproducible.")],
    [wrap_cell("Rule-based NLU (regex / keyword extraction)"), wrap_cell("main.py — _parse_intake"),
     wrap_cell("Extracts experience level, known skills and interest domains from conversational text to structure the profile.")],
    [wrap_cell("Multi-factor scoring"), wrap_cell("recommender.py — recommend()"),
     wrap_cell("Combines goal relevance (0.7 weight), new-skill coverage (0.3 weight) and a level-mismatch penalty into a single ranking score per course.")],
    [wrap_cell("Graph-based sequencing (topological sort)"), wrap_cell("path_generator.py"),
     wrap_cell("Models the course catalog as a DAG of prerequisites; guarantees a mathematically valid learning order, not just a relevance-ranked list.")],
    [wrap_cell("Grounded natural-language generation"), wrap_cell("explainer.py"),
     wrap_cell("Template-driven explanations strictly conditioned on computed scores/gaps — explainability-by-construction, avoiding hallucinated justifications.")],
]
story.append(styled_table(header, rows, [1.5 * inch, 1.35 * inch, 3.0 * inch]))
story.append(Spacer(1, 10))
story.append(body(
    "<b>Why not call an LLM directly for everything?</b> For a submission that needs to run "
    "reproducibly offline with no API key, TF-IDF + rule-based scoring + templated explanation is "
    "transparent, fast and traceable — every recommendation can be justified by pointing at the "
    "exact number that produced it. The architecture is intentionally modular so the explainer and "
    "intake parser can be swapped for an LLM call (e.g. Claude) that receives the same structured "
    "profile/course data as context, for richer free-form Q&amp;A, without touching the core "
    "recommendation or path-generation logic."
))

# ---------- 5. Key Features ----------
story.append(h1("5. Key Features & Workflows"))
story.append(bullets([
    "<b>Conversational intake</b> — no forms; a single free-text message populates the entire learner profile.",
    "<b>Explainable recommendations</b> — every roadmap step carries a one-sentence, data-grounded reason it's there.",
    "<b>Prerequisite-safe roadmap</b> — visualized as a trail with milestone markers for projects/assessments.",
    "<b>Adaptive re-planning</b> — mark-complete / \"too easy\" / \"too hard\" feedback immediately regenerates the path.",
    "<b>Progress dashboard</b> — overall completion %, per-domain progress, skills-acquired-vs-remaining chart, milestone tracker, next actions.",
    "<b>In-chat Q&amp;A</b> — learners can ask \"why is X in my path\", \"what's next\", or \"how long is left\".",
]))

# ---------- 6. Challenges ----------
story.append(h1("6. Challenges Faced & How They Were Addressed"))
story.append(bullets([
    "<b>Recommendations ignoring prerequisite order</b> — an early version scored and returned courses purely by relevance, risking suggesting an advanced course before its prerequisites. Solved by separating <i>what's relevant</i> (recommender) from <i>what order it must happen in</i> (path generator's DAG + topological sort).",
    "<b>Keeping progress stable as the path adapts</b> — completed courses were initially removed from the generated path, making the roadmap shrink and progress percentages meaningless over time. Fixed by keeping completed courses in the roadmap, flagged completed, so completion percentage is computed against a stable total.",
    "<b>Explanations that are actually trustworthy</b> — free-generated explanations risk sounding plausible while citing a reason not actually used by the scoring. Addressed by deriving every explanation sentence directly from the same score/skill-gap/prerequisite values the recommender computed.",
    "<b>Running without an LLM/API dependency</b> — to keep the submission fully reproducible without provisioning an API key, semantic matching uses TF-IDF instead of embeddings, with a documented extension path to an LLM-backed version.",
]))

story.append(PageBreak())

# ---------- 7. Cross-reference ----------
story.append(h1("7. Judging-Criteria Cross-Reference"))
header2 = ["Criterion", "Where addressed"]
rows2 = [
    [wrap_cell("Problem Understanding & Solution Design"), wrap_cell("Sections 1–3")],
    [wrap_cell("Functionality & Feature Completeness"), wrap_cell("All six \"what to build\" items implemented and wired end-to-end (see README deliverable table)")],
    [wrap_cell("AI/ML Implementation"), wrap_cell("Section 4")],
    [wrap_cell("Innovation & Creativity"), wrap_cell("Grounded/traceable explainability layer; DAG-based prerequisite sequencing rather than a flat ranked list; live adaptive regeneration on every feedback signal")],
    [wrap_cell("User Experience & Interface"), wrap_cell("Three-tab flow (Chat → Roadmap → Dashboard) mirrors the learner's mental model; custom \"trail map\" visual design")],
    [wrap_cell("Performance & Code Quality"), wrap_cell("Single-responsibility modules with docstrings; TF-IDF matrix built once at startup; typed REST API with Pydantic models")],
]
story.append(styled_table(header2, rows2, [2.1 * inch, 3.75 * inch]))

story.append(Spacer(1, 20))
story.append(h1("8. Known Limitations"))
story.append(bullets([
    "Learner profiles are stored in-memory (reset on backend restart) — production would use Postgres/SQLite.",
    "The course catalog (24 curated items) would be replaced by a real partner LMS catalog in production, with the TF-IDF index refreshed accordingly.",
    "Goal parsing uses TF-IDF + keyword extraction rather than a full NLU/LLM pipeline — robust for the demo goal styles, less so for highly unusual phrasing.",
]))

doc.build(story)
print("PDF generated.")
