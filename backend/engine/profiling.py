"""
Learner Profiling Engine
-------------------------
Captures and maintains a learner's profile: interests, stated goals,
experience level, completed courses/skills already known, and feedback
history used to adapt future recommendations.

For this prototype, profiles are stored in-memory (per learner_id). In a
production system this would be backed by a persistent database (see
README / documentation for the suggested production architecture).
"""

from datetime import datetime
from typing import Optional


class LearnerProfile:
    def __init__(self, learner_id: str, name: str = "Learner"):
        self.learner_id = learner_id
        self.name = name
        self.interests: list[str] = []
        self.goal_text: Optional[str] = None
        self.goal_domain: Optional[str] = None
        self.experience_level: str = "beginner"  # beginner | intermediate | advanced
        self.known_skills: set[str] = set()
        self.completed_course_ids: set[str] = set()
        self.in_progress_course_ids: set[str] = set()
        self.feedback_log: list[dict] = []
        self.feedback_flags: dict[str, str] = {}  # course_id -> latest feedback type, for visible badges
        self.created_at = datetime.utcnow().isoformat()

    def to_dict(self):
        return {
            "learner_id": self.learner_id,
            "name": self.name,
            "interests": self.interests,
            "goal_text": self.goal_text,
            "goal_domain": self.goal_domain,
            "experience_level": self.experience_level,
            "known_skills": sorted(self.known_skills),
            "completed_course_ids": sorted(self.completed_course_ids),
            "in_progress_course_ids": sorted(self.in_progress_course_ids),
            "feedback_log": self.feedback_log,
            "feedback_flags": self.feedback_flags,
            "created_at": self.created_at,
        }


class ProfileStore:
    """Simple in-memory profile store keyed by learner_id."""

    def __init__(self):
        self._profiles: dict[str, LearnerProfile] = {}

    def get_or_create(self, learner_id: str, name: str = "Learner") -> LearnerProfile:
        if learner_id not in self._profiles:
            self._profiles[learner_id] = LearnerProfile(learner_id, name)
        return self._profiles[learner_id]

    def get(self, learner_id: str) -> Optional[LearnerProfile]:
        return self._profiles.get(learner_id)

    def update_from_intake(self, learner_id: str, **kwargs) -> LearnerProfile:
        profile = self.get_or_create(learner_id)
        if "name" in kwargs and kwargs["name"]:
            profile.name = kwargs["name"]
        if "interests" in kwargs and kwargs["interests"]:
            profile.interests = list(set(profile.interests) | set(kwargs["interests"]))
        if "goal_text" in kwargs and kwargs["goal_text"]:
            profile.goal_text = kwargs["goal_text"]
        if "experience_level" in kwargs and kwargs["experience_level"]:
            profile.experience_level = kwargs["experience_level"]
        if "known_skills" in kwargs and kwargs["known_skills"]:
            profile.known_skills |= set(s.lower() for s in kwargs["known_skills"])
        if "completed_course_ids" in kwargs and kwargs["completed_course_ids"]:
            profile.completed_course_ids |= set(kwargs["completed_course_ids"])
        return profile

    def mark_course_complete(self, learner_id: str, course_id: str, skills_gained: list[str]):
        profile = self.get_or_create(learner_id)
        profile.completed_course_ids.add(course_id)
        profile.in_progress_course_ids.discard(course_id)
        profile.known_skills |= set(s.lower() for s in skills_gained)
        return profile

    def mark_course_in_progress(self, learner_id: str, course_id: str):
        profile = self.get_or_create(learner_id)
        profile.in_progress_course_ids.add(course_id)
        return profile

    def add_feedback(self, learner_id: str, course_id: str, feedback: str, comment: str = ""):
        profile = self.get_or_create(learner_id)
        profile.feedback_log.append({
            "course_id": course_id,
            "feedback": feedback,  # "too_easy" | "too_hard" | "not_relevant" | "helpful"
            "comment": comment,
            "timestamp": datetime.utcnow().isoformat(),
        })
        profile.feedback_flags[course_id] = feedback
        return profile

    def downgrade_experience(self, learner_id: str):
        """Step experience level down one notch (advanced->intermediate->beginner).
        Used when a learner flags a course as too hard, so the recommender
        actually responds to that signal instead of silently logging it."""
        order = ["beginner", "intermediate", "advanced"]
        profile = self.get_or_create(learner_id)
        idx = order.index(profile.experience_level) if profile.experience_level in order else 0
        if idx > 0:
            profile.experience_level = order[idx - 1]
        return profile

    def list_all(self):
        """Return a lightweight summary of every learner profile currently held in
        memory — used to power the roadmap switcher (no auth; browser-local list)."""
        return [
            {
                "learner_id": p.learner_id,
                "name": p.name,
                "goal_text": p.goal_text,
                "created_at": p.created_at,
            }
            for p in self._profiles.values()
        ]


# Singleton store used by the API layer
profile_store = ProfileStore()
