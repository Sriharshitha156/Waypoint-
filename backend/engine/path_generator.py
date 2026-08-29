"""
Learning Path Generator
-------------------------
Takes a set of "target" courses (the ones the recommendation engine says
are most relevant to the learner's goal) and expands them into a full,
prerequisite-safe roadmap:

  1. Expand each target course into its full prerequisite chain
     (recursively) so nothing is scheduled before its dependencies.
  2. Topologically sort the resulting course DAG using networkx.
  3. Skip anything the learner has already completed.
  4. Insert milestone checkpoints after logical groups (e.g. every
     domain "block", or after courses of type == assessment/project).
  5. Attach estimated duration and a running cumulative time estimate.
"""

import networkx as nx


def build_prerequisite_graph(course_by_id: dict, target_ids: list[str]):
    """Recursively collect target courses + all their prerequisites into a DAG."""
    graph = nx.DiGraph()
    visited = set()
    stack = list(target_ids)

    while stack:
        cid = stack.pop()
        if cid in visited or cid not in course_by_id:
            continue
        visited.add(cid)
        graph.add_node(cid)
        for prereq in course_by_id[cid]["prerequisites"]:
            graph.add_edge(prereq, cid)
            stack.append(prereq)

    return graph


def generate_path(course_by_id: dict, target_courses: list[dict], completed_course_ids: set[str],
                   feedback_flags: dict[str, str] | None = None):
    """Builds the full prerequisite-ordered roadmap for the target courses.

    Completed courses are kept IN the roadmap (marked completed=True) rather than
    removed, so the path stays stable and progress can be tracked against a fixed
    total instead of shrinking every time a course is finished.

    feedback_flags (course_id -> "too_easy"/"too_hard"/...) are attached to each
    step so the UI can show a visible acknowledgement instead of silently logging it.
    """
    feedback_flags = feedback_flags or {}
    target_ids = [c["id"] for c in target_courses]
    graph = build_prerequisite_graph(course_by_id, target_ids)

    try:
        ordered_ids = list(nx.topological_sort(graph))
    except nx.NetworkXUnfeasible:
        # Cycle detected (shouldn't happen with curated data) — fall back to insertion order
        ordered_ids = list(graph.nodes)

    steps = []
    cumulative_hours = 0
    step_number = 0

    for cid in ordered_ids:
        course = course_by_id[cid]
        step_number += 1
        cumulative_hours += course["duration_hours"]

        steps.append({
            "step": step_number,
            "course_id": cid,
            "title": course["title"],
            "type": course["type"],
            "domain": course["domain"],
            "level": course["level"],
            "duration_hours": course["duration_hours"],
            "skills_taught": course["skills_taught"],
            "prerequisites": course["prerequisites"],
            "is_explicit_target": cid in target_ids,
            "is_milestone": course["type"] in ("project", "assessment"),
            "completed": cid in completed_course_ids,
            "feedback_flag": feedback_flags.get(cid),
            "cumulative_hours": cumulative_hours,
        })

    return {
        "total_steps": len(steps),
        "total_estimated_hours": cumulative_hours,
        "steps": steps,
    }
