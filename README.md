# Pathfinder — AI-Powered Personalized Learning Path Recommender

An intelligent learning assistant that turns a free-text learning goal into a
structured, prerequisite-ordered learning roadmap — with explanations for
every recommendation, adaptive re-planning based on feedback/progress, and a
progress dashboard.

## What's included

| Deliverable (from the brief)              | Where it lives |
|--------------------------------------------|----------------|
| Conversational interface                   | Chat tab (`frontend/`) → `POST /api/chat`, `POST /api/ask/{id}` |
| Learner profiling engine                   | `backend/engine/profiling.py` |
| Recommendation engine                      | `backend/engine/recommender.py` (TF-IDF + rule-based scoring) |
| Personalized path generator w/ prerequisites & milestones | `backend/engine/path_generator.py` (topological sort over a course DAG) |
| Explainability / Q&A assistant             | `backend/engine/explainer.py` |
| Progress dashboard                         | Dashboard tab (`frontend/`) → `GET /api/dashboard/{id}` |

## Architecture

```
frontend/ (static, no build step — React + Chart.js via CDN)
   index.html   entry point, loads React/Babel/Chart.js from CDN
   app.jsx      chat / roadmap / dashboard UI (JSX, transpiled in-browser)
   styles.css   visual design ("trail map" theme)
        │
        │  fetch() — REST/JSON
        ▼
backend/ (FastAPI, Python)
   main.py                 REST API — orchestrates the engines below
   engine/profiling.py     learner profile store (interests, goal, skills, history)
   engine/recommender.py   TF‑IDF goal matcher + course scoring (skill-gap aware)
   engine/path_generator.py  prerequisite graph (networkx) → topological roadmap
   engine/explainer.py     turns scores/gaps into natural-language explanations
   data/courses.json       course catalog (24 courses/projects/assessments,
                            6 domains, with prerequisites & tags)
```

No external AI API key is required to run this prototype — the goal-matching
and explanation layers are self-contained (TF-IDF + rule-based), so it runs
fully offline. The codebase is structured so the `explainer.py` / intake
parser could be swapped for a call to an LLM (e.g. the Claude API) with the
same structured profile/path data as context — see
`docs/SOLUTION_DOCUMENTATION.md` for that extension path.

## Prerequisites

- Python 3.10+
- A modern browser (Chrome/Firefox/Edge). No Node.js or `npm install` needed
  for the frontend — it loads React/Babel/Chart.js from CDNs at runtime.

## Setup & run

### 1. Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The API is now live at `http://127.0.0.1:8000` (interactive docs at
`http://127.0.0.1:8000/docs`).

### 2. Frontend

In a second terminal:

```bash
cd frontend
python -m http.server 8090
```

Open `http://127.0.0.1:8090` in your browser.

> The frontend calls the backend at `http://127.0.0.1:8000` by default
> (see `window.API_BASE` in `frontend/index.html`). Change that value if
> your backend runs on a different host/port.

### 3. Try it

1. In the **Chat** tab, describe a goal, e.g.:
   *"I'm a complete beginner and want to become a machine learning engineer"*
2. The assistant infers your domain, experience level and any skills you
   mentioned, then builds a roadmap — visible in the **Roadmap** tab.
3. Mark a step complete, or give feedback ("too easy" / "too hard") — the
   path adapts immediately.
4. Check the **Dashboard** tab for progress, skill development and
   upcoming milestones.
5. Ask the assistant follow-up questions like *"why is this course here"*
   or *"what's next"* in the Chat tab.

## Running tests / sanity-checking the API directly

```bash
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"learner_id":"demo","message":"I want to become a full-stack web developer, total beginner"}'
```

Full endpoint list and docstrings are in `backend/main.py`, or visit
`/docs` for the interactive Swagger UI once the server is running.

## Design notes / key decisions

- **Goal understanding without an external LLM dependency**: goals are
  matched to courses using TF-IDF + cosine similarity over course titles,
  tags, descriptions and taught skills. This keeps the prototype
  self-contained and reproducible, while remaining swappable for an
  embeddings/LLM-based matcher in production.
- **Prerequisite-safe paths**: the course catalog is modeled as a directed
  acyclic graph; `networkx.topological_sort` guarantees a course's
  prerequisites always appear earlier in the generated path.
- **Traceable explanations**: every "why this course" explanation is
  generated from the actual computed relevance score, skill gap and
  prerequisite state — not free-generated text — so it can't hallucinate a
  reason unconnected to the underlying recommendation.
- **Adaptation loop**: completing a course, or flagging one as "too easy"
  (skills folded into `known_skills`) or "too hard", triggers an immediate
  path regeneration, so the roadmap always reflects the latest profile.
- **Stateless-friendly regeneration**: the path is fully recomputed (not
  incrementally patched) on every profile change, which keeps the system
  simple and avoids state drift, at the cost of some recompute — fine at
  this catalog size.

## Known limitations of this prototype

- Learner profiles are stored in-memory (reset when the backend restarts).
  A production build would back this with Postgres/SQLite.
- The course catalog (`backend/data/courses.json`) is a curated seed set of
  24 items; a production system would ingest a real course catalog (e.g.
  from a partner LMS) and refresh the TF-IDF index accordingly.
- Goal parsing uses TF-IDF + keyword extraction rather than a true NLU/LLM
  pipeline; it works well for the demo goals but is less robust to very
  unusual phrasing. See `docs/SOLUTION_DOCUMENTATION.md` for how this would
  be upgraded.

## License

Prototype built for evaluation purposes.
