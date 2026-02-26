import copy
from resume_intel import apply_intelligence

JD_FE = """
Junior Frontend Engineer. Build user-facing interfaces using ReactJS, JavaScript, HTML, CSS.
Reusable UI components, client-side state, responsive layouts, cross-browser compatibility.
Accessibility: ARIA, keyboard navigation, semantic HTML.
Integrate frontend components with REST APIs. Git and code reviews.
"""

JD_BE = """
Junior Backend Engineer. Build backend services and REST APIs using Python.
SQL queries for relational databases, CRUD operations, MongoDB familiarity.
Validation, error handling, auth basics. Unit tests, integration tests. Git.
"""

JD_FS = """
Junior Full Stack Engineer. ReactJS frontend plus Python/Java backend and SQL.
Design and consume REST APIs, relational DB + MongoDB, HTML/CSS/JavaScript.
Tests for both layers. Git, code reviews, end-to-end features.
"""

def run(jd: str, role_family: str):
    master = {"summary": "", "skills": {"Core": []}, "projects": [], "experience": []}
    return apply_intelligence(copy.deepcopy(master), role_family=role_family, jd_text=jd, summary_mode="auto")

def test_archetype_frontend_despite_api_terms():
    out = run(JD_FE, "Frontend Developer")
    assert out.get("_jd_archetype") == "FRONTEND_WEB"

def test_archetype_backend_despite_frontend_mentions():
    out = run(JD_BE + " Nice to have: React dashboards occasionally.", "Backend Developer")
    assert out.get("_jd_archetype") == "BACKEND_WEB"

def test_archetype_fullstack_when_fe_and_be_present():
    out = run(JD_FS, "Full Stack Developer")
    assert out.get("_jd_archetype") == "FULLSTACK_WEB"
