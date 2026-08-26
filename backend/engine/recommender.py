"""
Recommendation Engine
----------------------
Two responsibilities:

1. Goal Understanding: turn a learner's free-text goal ("I want to become
   a machine learning engineer") into a structured target — a ranked list
   of candidate courses/domains most relevant to that goal — using TF-IDF
   vectorization + cosine similarity over the course catalog (title, tags,
   description, skills). This acts as a lightweight semantic matcher
   without requiring an external embedding API, so the prototype runs
   fully offline.

2. Course Recommendation / Skill-Gap Analysis: given a learner profile
   (known skills, completed courses, experience level) and a target
   domain, score every course by relevance to the goal, prerequisite
   readiness, and novelty (skills not already known).
"""

import json
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "courses.json")


def load_courses():
    with open(DATA_PATH, "r") as f:
        return json.load(f)


class RecommendationEngine:
    def __init__(self):
        self.courses = load_courses()
        self.course_by_id = {c["id"]: c for c in self.courses}
        self._corpus = [self._course_text(c) for c in self.courses]
        self.vectorizer = TfidfVectorizer(stop_words="english")
        self.course_matrix = self.vectorizer.fit_transform(self._corpus)

    @staticmethod
    def _course_text(course: dict) -> str:
        return " ".join([
            course["title"],
            course["domain"],
            course["description"],
            " ".join(course["tags"]),
            " ".join(course["skills_taught"]),
        ])

    def match_goal_to_courses(self, goal_text: str, top_k: int = 8):
        """Return top-k courses most semantically similar to the free-text goal."""
        goal_vec = self.vectorizer.transform([goal_text])
        sims = cosine_similarity(goal_vec, self.course_matrix).flatten()
        ranked_idx = sims.argsort()[::-1][:top_k]
        results = []
        for i in ranked_idx:
            if sims[i] <= 0:
                continue
            results.append({**self.courses[i], "similarity": round(float(sims[i]), 4)})
        return results

    def infer_domain(self, goal_text: str) -> str:
        matches = self.match_goal_to_courses(goal_text, top_k=5)
        if not matches:
            return "General"
        domain_scores: dict[str, float] = {}
        for m in matches:
            domain_scores[m["domain"]] = domain_scores.get(m["domain"], 0) + m["similarity"]
        return max(domain_scores, key=domain_scores.get)

    def skill_gap(self, known_skills: set[str], target_courses: list[dict]) -> list[str]:
        needed = set()
        for c in target_courses:
            needed |= set(s.lower() for s in c["skills_taught"])
        return sorted(needed - set(s.lower() for s in known_skills))

    def recommend(self, goal_text: str, known_skills: set[str], completed_course_ids: set[str],
                   experience_level: str, top_k: int = 12):
        """
        Score every course against the goal + learner profile.
        Score = semantic relevance to goal
              + bonus if it teaches skills the learner doesn't have yet
              - penalty if already completed
              - small penalty if level mismatches experience too far
        """
        goal_vec = self.vectorizer.transform([goal_text])
        sims = cosine_similarity(goal_vec, self.course_matrix).flatten()

        level_rank = {"beginner": 0, "intermediate": 1, "advanced": 2}
        learner_rank = level_rank.get(experience_level, 0)

        scored = []
        for idx, course in enumerate(self.courses):
            if course["id"] in completed_course_ids:
                continue
            relevance = float(sims[idx])
            new_skill_ratio = 0
            taught = set(s.lower() for s in course["skills_taught"])
            if taught:
                new_skill_ratio = len(taught - set(s.lower() for s in known_skills)) / len(taught)

            course_rank = level_rank.get(course["level"], 1)
            level_penalty = 0.05 * abs(course_rank - learner_rank)

            score = (0.7 * relevance) + (0.3 * new_skill_ratio) - level_penalty
            scored.append({**course, "score": round(score, 4), "relevance": round(relevance, 4)})

        scored.sort(key=lambda c: c["score"], reverse=True)
        return scored[:top_k]


engine = RecommendationEngine()
