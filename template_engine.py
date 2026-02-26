import json
from pathlib import Path

TEMPLATES_PATH = Path("data") / "resume_templates.json"

DEFAULT_TEMPLATES = {
    "software_engineer_classic": {
        "label": "Software Engineer (Classic ATS)",
        "sections": ["Header", "Summary", "Skills", "Experience", "Projects", "Education", "Publications"],
    },
    "java_fullstack": {
        "label": "Java Full Stack",
        "sections": ["Header", "Summary", "Skills", "Experience", "Projects", "Education", "Publications"],
        "boost_keywords": ["java", "spring", "spring boot", "microservices", "rest", "sql"],
    },
    "react_frontend": {
        "label": "React Frontend",
        "sections": ["Header", "Summary", "Skills", "Projects", "Experience", "Education", "Publications"],
        "boost_keywords": ["react", "javascript", "html", "css"],
    },
    "data_analyst": {
        "label": "Data Analyst",
        "sections": ["Header", "Summary", "Skills", "Projects", "Experience", "Education", "Publications"],
        "boost_keywords": ["sql", "power bi", "tableau", "excel", "dashboard", "python", "pandas"],
    },
    "consulting_general": {
        "label": "Consulting / General",
        "sections": ["Header", "Summary", "Skills", "Experience", "Projects", "Education", "Publications"],
    },
    "minimal_one_page": {
        "label": "Minimal One Page",
        "sections": ["Header", "Summary", "Skills", "Projects", "Experience", "Education"],
    },
}

def load_templates() -> dict:
    if not TEMPLATES_PATH.exists():
        TEMPLATES_PATH.parent.mkdir(exist_ok=True)
        TEMPLATES_PATH.write_text(json.dumps(DEFAULT_TEMPLATES, indent=2), encoding="utf-8")
    return json.loads(TEMPLATES_PATH.read_text(encoding="utf-8"))

def pick_template(role_family: str, jd_keywords: list[str]) -> tuple[str, dict, dict]:
    """
    Returns: (template_id, template_obj, debug_info)
    """
    templates = load_templates()
    kws = {k.lower() for k in (jd_keywords or [])}

    # Role-family hinting
    if role_family in ("JAVA_FULLSTACK",):
        preferred = "java_fullstack"
    elif role_family in ("DATA_ANALYST",):
        preferred = "data_analyst"
    elif role_family in ("REACT_FRONTEND",):
        preferred = "react_frontend"
    else:
        preferred = "software_engineer_classic"

    # Score templates by keyword overlap (simple + effective)
    scores = {}
    for tid, t in templates.items():
        boost = set(map(str.lower, t.get("boost_keywords", [])))
        scores[tid] = len(boost.intersection(kws))

    best_by_kw = max(scores, key=scores.get) if scores else preferred

    # Choose: if keyword score meaningful, use it; else use role hint
    chosen = best_by_kw if scores.get(best_by_kw, 0) >= 2 else preferred
    return chosen, templates[chosen], {"role_family": role_family, "scores": scores, "chosen": chosen}
