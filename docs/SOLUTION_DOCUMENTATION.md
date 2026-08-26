# Pathfinder: AI-Powered Personalized Learning Path Recommender

## Solution Documentation

---

## 1. Problem Understanding

Online learning platforms have solved *content discovery* (thousands of
courses, searchable and tagged) but not *sequencing*. A learner who knows
they want to "become a data scientist" is still left to manually figure out:

- which of hundreds of courses are actually relevant to that goal,
- what order to take them in given prerequisite knowledge,
- whether they already know some of the material,
- how to prove they've learned it (projects/assessments), and
- what to do when a course turns out to be too easy, too hard, or their
  goal shifts.

A one-size-fits-all "top 10 courses in Data Science" list ignores the
learner's starting point entirely. The core problem is therefore not
recommendation in isolation — it's **goal-conditioned sequencing with
continuous adaptation**: profile the learner, understand the goal,
identify the skill gap between them, and produce an ordered, explainable,
living roadmap.

## 2. Solution Approach

Pathfinder is built around four cooperating engines, each with a single
responsibility, orchestrated by a thin API layer:

1. **Learner Profiling Engine** — captures interests, free-text goal,
   experience level, known skills, completed/in-progress courses, and a
   feedback log, built up conversationally rather than through a long form.
2. **Recommendation Engine** — matches the learner's free-text goal against
   a course catalog using TF-IDF + cosine similarity (a lightweight
   semantic matcher), then re-scores candidates against the learner's
   *specific* profile: relevance to goal, proportion of newly-taught
   skills, and a small penalty for level mismatch.
3. **Learning Path Generator** — expands the top-matched courses into their
   full prerequisite chains (a directed acyclic graph), topologically sorts
   them, and annotates milestones (projects/assessments) and cumulative
   time estimates.
4. **Explainability Layer** — turns the structured scores/gaps/prerequisite
   state from the engines above into natural-language explanations and
   answers to learner questions ("why this course", "what's next", "how
   long left") — grounded strictly in the computed data, so it cannot
   invent a justification unconnected to the actual recommendation.

A learner interacts entirely through natural language in the chat
interface; behind the scenes every message updates the profile and
triggers a full path regeneration, so the roadmap is always a live
reflection of the latest known state.

## 3. System Architecture

```
┌─────────────────────────────┐        ┌──────────────────────────────────┐
│  Frontend (static, no build)│  REST  │  Backend (FastAPI)                │
│  ─────────────────────────  │◄──────►│  ────────────────────────────────│
│  Chat tab   → intake / Q&A  │  JSON  │  main.py — API orchestration      │
│  Roadmap tab→ trail view    │        │  engine/profiling.py              │
│  Dashboard  → progress viz  │        │  engine/recommender.py (TF-IDF)   │
│  React + Chart.js via CDN   │        │  engine/path_generator.py (DAG)   │
└─────────────────────────────┘        │  engine/explainer.py              │
                                        │  data/courses.json (catalog)      │
                                        └──────────────────────────────────┘
```

**Data flow for a new goal:**
`chat message → intake parser (level/skills/interests) → profile update
→ TF-IDF goal↔course matching → skill-gap scored ranking → prerequisite
expansion → topological sort → explanation generation → roadmap returned
to UI`

**Data flow for adaptation:**
`mark complete / feedback → profile update (known_skills, completed_ids)
→ full path regeneration → UI reflects new roadmap + dashboard stats`

## 4. AI / ML Techniques Used

| Technique | Where | Why |
|---|---|---|
| **TF-IDF vectorization + cosine similarity** | `recommender.py` | Matches free-text goals to the most semantically relevant courses without requiring an external embeddings API — keeps the prototype fully offline and reproducible. |
| **Rule-based NLU (regex/keyword extraction)** | `main.py::_parse_intake` | Extracts experience level, known skills and interest domains from conversational text to structure the profile. |
| **Multi-factor scoring** | `recommender.py::recommend` | Combines goal relevance (0.7 weight), new-skill coverage (0.3 weight) and a level-mismatch penalty into a single ranking score per course. |
| **Graph-based sequencing (topological sort)** | `path_generator.py` | Models the course catalog as a DAG of prerequisites; guarantees a mathematically valid learning order, not just a relevance-ranked list. |
| **Grounded natural-language generation** | `explainer.py` | Template-driven explanation generation strictly conditioned on computed scores/gaps — an explainability-by-construction approach that avoids hallucinated justifications. |

**Why not call an LLM directly for everything?** For a submission that
needs to run reproducibly offline with no API key, TF-IDF + rule-based
scoring + templated explanation is transparent, fast and traceable — every
recommendation can be justified by pointing at the exact number that
produced it. The architecture is intentionally modular so `explainer.py`
and `_parse_intake` can be swapped for an LLM call (e.g. Claude) that
receives the same structured profile/course data as context, for richer
free-form Q&A — without touching the recommendation or path-generation
core.

## 5. Key Features & Workflows

- **Conversational intake** — no forms; a single free-text message ("I'm a
  beginner who knows some Python and want to become an ML engineer")
  populates the entire learner profile.
- **Explainable recommendations** — every step in the roadmap carries a
  one-sentence, data-grounded reason it's there.
- **Prerequisite-safe roadmap** — visualized as a trail with milestone
  markers for projects/assessments.
- **Adaptive re-planning** — three feedback actions (mark complete, "too
  easy", "too hard") immediately regenerate the path; "too easy" folds the
  course's skills into the learner's known-skills set so it doesn't get
  re-recommended.
- **Progress dashboard** — overall completion %, per-domain progress bars,
  a skills-acquired-vs-remaining chart, milestone tracker, and "what's
  next" panel.
- **In-chat Q&A** — learners can ask "why is X in my path", "what's next",
  or "how long is left" and get answers grounded in the live roadmap.

## 6. Challenges Faced & How They Were Addressed

- **Avoiding recommendations that ignore prerequisite order**: an early
  version scored and returned courses purely by relevance, which could
  suggest an advanced course before its prerequisites. Solved by
  separating *what's relevant* (recommender) from *what order it must
  happen in* (path generator's DAG + topological sort) as distinct stages.
- **Keeping "progress" stable as the path adapts**: initially, completed
  courses were removed from the generated path entirely, which made the
  roadmap shrink and progress percentages meaningless across sessions.
  Fixed by keeping completed courses *in* the roadmap, flagged `completed:
  true`, so completion percentage is computed against a stable total.
- **Explanations that are actually trustworthy**: free-generated
  explanations risk sounding plausible while citing a reason not actually
  used by the scoring — addressed by deriving every explanation sentence
  directly from the same score/skill-gap/prerequisite values the
  recommender computed, rather than a separate generation pass.
- **Running without an LLM/API dependency**: to keep the submission fully
  reproducible without provisioning an API key, semantic matching uses
  TF-IDF instead of embeddings — a deliberate trade-off documented above,
  with a clear extension path to an LLM-backed version.

## 7. Judging-Criteria Cross-Reference

- **Problem understanding & design** — Section 1–3.
- **Functionality & completeness** — all six "what to build" items are
  implemented and wired end-to-end (see README's deliverable table).
- **AI/ML implementation** — Section 4.
- **Innovation** — grounded/traceable explainability layer; DAG-based
  prerequisite sequencing rather than a flat ranked list; live adaptive
  regeneration on every feedback signal.
- **UX/UI** — three-tab flow (Chat → Roadmap → Dashboard) mirrors the
  learner's actual mental model (describe goal → see the plan → track
  progress); custom "trail map" visual design rather than a generic
  dashboard template.
- **Performance & code quality** — engines are single-responsibility
  modules with docstrings; catalog-size TF-IDF matrix is built once at
  startup; REST API is documented and typed with Pydantic models.
