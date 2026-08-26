"""
AI-Powered Personalized Learning Path Recommender — Backend
==============================================================
FastAPI application exposing:

  POST /api/chat                 conversational intake -> updates profile, returns assistant reply
  POST /api/profile/{id}         manually create/update a learner profile
  GET  /api/profile/{id}         fetch a learner profile
  POST /api/path/{id}/generate   generate/regenerate the personalized learning path
  GET  /api/path/{id}            fetch the last generated path
  POST /api/progress/{id}        mark a course complete / in-progress
  POST /api/feedback/{id}        submit feedback on a course (too easy/hard/not relevant)
  POST /api/ask/{id}             ask the assistant a question about the current path
  GET  /api/courses              list full course catalog (for dashboard / debugging)
  GET  /api/dashboard/{id}       aggregated data for the progress dashboard

Run with:  uvicorn main:app --reload --port 8000
"""

import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from engine.profiling import profile_store
from engine.recommender import engine as rec_engine
from engine.path_generator import generate_path
from engine.explainer import explain_course_recommendation, explain_path_overview, answer_query

app = FastAPI(title="AI Learning Path Recommender API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory cache of the last generated path per learner
_path_cache: dict[str, dict] = {}

LEVEL_KEYWORDS = {
    "beginner": ["beginner", "new to", "never coded", "no experience", "from scratch", "just starting"],
    "advanced": ["advanced", "expert", "years of experience", "senior", "already know", "experienced"],
    "intermediate": ["intermediate", "some experience", "familiar with"],
}

KNOWN_SKILL_KEYWORDS = [
    "python", "sql", "javascript", "java", "html", "css", "statistics", "excel",
    "react", "nodejs", "docker", "aws", "pandas", "numpy",
]


class ChatMessage(BaseModel):
    learner_id: str
    message: str
    name: str | None = None


class ProfileUpdate(BaseModel):
    name: str | None = None
    interests: list[str] | None = None
    goal_text: str | None = None
    experience_level: str | None = None
    known_skills: list[str] | None = None
    completed_course_ids: list[str] | None = None


class ProgressUpdate(BaseModel):
    course_id: str
    status: str  # "completed" | "in_progress"


class FeedbackInput(BaseModel):
    course_id: str
    feedback: str  # "too_easy" | "too_hard" | "not_relevant" | "helpful"
    comment: str | None = ""


class AskInput(BaseModel):
    query: str


def _parse_intake(message: str) -> dict:
    """Lightweight rule-based NLU: pull experience level + known skills mentioned in free text.
    The goal text itself is passed through as-is to the TF-IDF matcher, which handles the
    semantic matching — this function only extracts structured side-signals."""
    text = message.lower()

    experience_level = None
    for level, kws in LEVEL_KEYWORDS.items():
        if any(kw in text for kw in kws):
            experience_level = level
            break

    known_skills = [s for s in KNOWN_SKILL_KEYWORDS if re.search(rf"\b{re.escape(s)}\b", text)]

    interests = re.findall(
        r"(data science|machine learning|web development|deep learning|cloud|nlp|"
        r"artificial intelligence|frontend|backend|full.?stack|product management|ux design|"
        r"data engineering|generative ai|devops)",
        text,
    )

    return {
        "experience_level": experience_level,
        "known_skills": known_skills,
        "interests": list(set(interests)),
    }


def _build_path_for_learner(profile) -> dict:
    goal_text = profile.goal_text or ", ".join(profile.interests) or "general skill development"
    domain = rec_engine.infer_domain(goal_text)
    top_matches = rec_engine.match_goal_to_courses(goal_text, top_k=6)
    scored = rec_engine.recommend(
        goal_text=goal_text,
        known_skills=profile.known_skills,
        completed_course_ids=profile.completed_course_ids,
        experience_level=profile.experience_level,
        top_k=8,
    )
    target_courses = top_matches if top_matches else scored[:5]
    path = generate_path(rec_engine.course_by_id, target_courses, profile.completed_course_ids)

    for step in path["steps"]:
        course = rec_engine.course_by_id[step["course_id"]]
        scored_version = next((c for c in scored if c["id"] == step["course_id"]), course)
        step["explanation"] = explain_course_recommendation(scored_version, profile.known_skills, goal_text)

    path["goal_text"] = goal_text
    path["domain"] = domain
    path["overview"] = explain_path_overview(path, goal_text, domain)
    _path_cache[profile.learner_id] = path
    return path


@app.post("/api/chat")
def chat(msg: ChatMessage):
    parsed = _parse_intake(msg.message)
    profile = profile_store.update_from_intake(
        msg.learner_id,
        name=msg.name,
        goal_text=msg.message,
        experience_level=parsed["experience_level"],
        known_skills=parsed["known_skills"],
        interests=parsed["interests"],
    )

    path = _build_path_for_learner(profile)

    reply = (
        f"Thanks{', ' + profile.name if profile.name and profile.name != 'Learner' else ''}! "
        f"I've mapped your goal to the **{path['domain']}** track. {path['overview']} "
        f"Your first step is **{path['steps'][0]['title']}**. "
        f"Ask me things like 'why this course' or 'what's next' any time."
    )

    return {
        "reply": reply,
        "profile": profile.to_dict(),
        "path": path,
    }


@app.post("/api/profile/{learner_id}")
def update_profile(learner_id: str, update: ProfileUpdate):
    profile = profile_store.update_from_intake(learner_id, **update.dict(exclude_none=True))
    return profile.to_dict()


@app.get("/api/profile/{learner_id}")
def get_profile(learner_id: str):
    profile = profile_store.get(learner_id)
    if not profile:
        raise HTTPException(404, "Learner profile not found")
    return profile.to_dict()


@app.post("/api/path/{learner_id}/generate")
def generate_learner_path(learner_id: str):
    profile = profile_store.get(learner_id)
    if not profile:
        raise HTTPException(404, "Learner profile not found. Chat with the assistant first.")
    return _build_path_for_learner(profile)


@app.get("/api/path/{learner_id}")
def get_learner_path(learner_id: str):
    if learner_id not in _path_cache:
        raise HTTPException(404, "No path generated yet for this learner.")
    return _path_cache[learner_id]


@app.post("/api/progress/{learner_id}")
def update_progress(learner_id: str, update: ProgressUpdate):
    profile = profile_store.get(learner_id)
    if not profile:
        raise HTTPException(404, "Learner profile not found")
    course = rec_engine.course_by_id.get(update.course_id)
    if not course:
        raise HTTPException(404, "Course not found")

    if update.status == "completed":
        profile_store.mark_course_complete(learner_id, update.course_id, course["skills_taught"])
    elif update.status == "in_progress":
        profile_store.mark_course_in_progress(learner_id, update.course_id)
    else:
        raise HTTPException(400, "status must be 'completed' or 'in_progress'")

    path = _build_path_for_learner(profile)
    return {"profile": profile.to_dict(), "path": path}


@app.post("/api/feedback/{learner_id}")
def submit_feedback(learner_id: str, fb: FeedbackInput):
    profile = profile_store.get(learner_id)
    if not profile:
        raise HTTPException(404, "Learner profile not found")

    profile_store.add_feedback(learner_id, fb.course_id, fb.feedback, fb.comment or "")

    # Adapt: "too_easy" -> treat as known skill (skip it); "not_relevant" -> exclude via completion
    course = rec_engine.course_by_id.get(fb.course_id)
    if course and fb.feedback == "too_easy":
        profile.known_skills |= set(s.lower() for s in course["skills_taught"])
    if course and fb.feedback in ("too_easy", "not_relevant"):
        profile.completed_course_ids.add(fb.course_id)

    path = _build_path_for_learner(profile)
    return {"profile": profile.to_dict(), "path": path}


@app.post("/api/ask/{learner_id}")
def ask_assistant(learner_id: str, ask: AskInput):
    profile = profile_store.get(learner_id)
    if not profile:
        raise HTTPException(404, "Learner profile not found")
    path = _path_cache.get(learner_id)
    if not path:
        path = _build_path_for_learner(profile)
    reply = answer_query(ask.query, profile, path, rec_engine.course_by_id)
    return {"reply": reply}


@app.get("/api/courses")
def list_courses():
    return rec_engine.courses


@app.get("/api/dashboard/{learner_id}")
def dashboard(learner_id: str):
    profile = profile_store.get(learner_id)
    if not profile:
        raise HTTPException(404, "Learner profile not found")
    path = _path_cache.get(learner_id) or _build_path_for_learner(profile)

    total = path["total_steps"]
    completed = len([s for s in path["steps"] if s["course_id"] in profile.completed_course_ids])
    in_progress = [s for s in path["steps"] if s["course_id"] in profile.in_progress_course_ids]
    upcoming = [s for s in path["steps"] if s["course_id"] not in profile.completed_course_ids][:3]

    # Skill development: known skills vs skills still to acquire in the path
    skills_in_path = set()
    for s in path["steps"]:
        skills_in_path |= set(x.lower() for x in s["skills_taught"])
    skills_acquired = skills_in_path & profile.known_skills
    skills_remaining = skills_in_path - profile.known_skills

    domain_progress: dict[str, dict] = {}
    for s in path["steps"]:
        d = domain_progress.setdefault(s["domain"], {"total": 0, "completed": 0})
        d["total"] += 1
        if s["course_id"] in profile.completed_course_ids:
            d["completed"] += 1

    return {
        "learner": profile.to_dict(),
        "progress_percent": round(100 * completed / total, 1) if total else 0,
        "total_steps": total,
        "completed_steps": completed,
        "in_progress": in_progress,
        "upcoming_next": upcoming,
        "skills_acquired": sorted(skills_acquired),
        "skills_remaining": sorted(skills_remaining),
        "domain_progress": domain_progress,
        "total_estimated_hours": path["total_estimated_hours"],
        "milestones": [s for s in path["steps"] if s["is_milestone"]],
    }


@app.get("/")
def root():
    return {"status": "ok", "message": "AI Learning Path Recommender API is running."}
