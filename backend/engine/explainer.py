"""
Explainability Module
-----------------------
Generates human-readable explanations for why a course was recommended
and for the overall shape of the learning path. Also powers the
conversational assistant's answers to "why" / "what's next" style
queries.

This is template + data driven (grounded strictly in the actual scores,
prerequisites and skill gaps computed by the other engines) rather than
a free-generating LLM, so every explanation is traceable and won't
hallucinate a reason that isn't backed by the underlying data. In a
production build this layer could be swapped for an LLM call that is
GIVEN this same structured data as context (see documentation).
"""


def explain_course_recommendation(course: dict, known_skills: set[str], goal_text: str) -> str:
    taught = set(s.lower() for s in course["skills_taught"])
    new_skills = taught - set(s.lower() for s in known_skills)

    reasons = []
    if course.get("relevance", 0) > 0.15 or course.get("similarity", 0) > 0.15:
        reasons.append(f"it closely matches your stated goal (\"{goal_text.strip()}\")")
    if new_skills:
        skills_str = ", ".join(sorted(new_skills)[:4])
        reasons.append(f"it teaches skills you don't have yet ({skills_str})")
    if course["prerequisites"]:
        reasons.append("its prerequisites fit what you already know or are about to complete")
    else:
        reasons.append("it has no prerequisites, so it's a safe starting point")
    if course["type"] == "project":
        reasons.append("it gives you a portfolio-worthy project to prove the skill")
    if course["type"] == "assessment":
        reasons.append("it validates your understanding before you move to harder material")

    reason_text = "; ".join(reasons)
    return f"\"{course['title']}\" is recommended because {reason_text}."


def explain_path_overview(path: dict, goal_text: str, domain: str) -> str:
    total_hours = path["total_estimated_hours"]
    total_steps = path["total_steps"]
    milestones = [s for s in path["steps"] if s["is_milestone"]]
    return (
        f"Based on your goal — \"{goal_text.strip()}\" — this path focuses on {domain} and is made up of "
        f"{total_steps} steps (~{total_hours} hours total), including {len(milestones)} project/assessment "
        f"milestones so you can prove each skill before moving on. Courses are ordered so prerequisites "
        f"always come before the material that depends on them."
    )


def answer_query(query: str, profile, path: dict, course_by_id: dict) -> str:
    """Very lightweight intent matching for the chat assistant's Q&A about the path."""
    q = query.lower()

    if any(k in q for k in ["next", "what should i do", "what now", "start with"]):
        remaining = [s for s in path["steps"] if s["course_id"] not in profile.completed_course_ids]
        if not remaining:
            return "You've completed everything in your current path. Consider setting a new goal to generate the next stage of your roadmap."
        nxt = remaining[0]
        return f"Your next recommended step is \"{nxt['title']}\" ({nxt['duration_hours']}h, {nxt['level']} level)."

    if any(k in q for k in ["how long", "how much time", "duration", "hours"]):
        return f"Your current path totals approximately {path['total_estimated_hours']} hours across {path['total_steps']} steps."

    if any(k in q for k in ["why", "reason", "recommend"]):
        for cid_name in course_by_id:
            if cid_name.replace("-", " ") in q or course_by_id[cid_name]["title"].lower() in q:
                course = course_by_id[cid_name]
                return explain_course_recommendation(course, profile.known_skills, profile.goal_text or "")
        return "Ask me 'why [course name]' and I'll explain exactly why it's in your path."

    if any(k in q for k in ["skip", "too easy", "already know"]):
        return "Got it — tell me which course felt too easy (e.g. 'this was too easy: Python Programming Fundamentals') and I'll mark it as known and adjust your path."

    if any(k in q for k in ["hard", "difficult", "struggling"]):
        return "That's useful feedback — I can insert an easier bridging course before that topic, or slow the pace. Tell me the course name and I'll adjust your path."

    return ("I can explain any recommendation ('why is X in my path'), tell you what's next, "
            "estimate remaining time, or adjust your path based on feedback. What would you like to know?")
