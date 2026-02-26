import copy
from resume_intel import apply_intelligence
from tests._helpers import FRONTEND_JD, BACKEND_JD, FULLSTACK_JD, first_skills_bucket_text

def test_frontend_summary_gate():
    master = {"summary": "", "skills": {"Core": ["React", "TypeScript", "CSS"]}, "projects": [], "experience": []}
    out = apply_intelligence(copy.deepcopy(master), role_family="Frontend Developer", jd_text=FRONTEND_JD, summary_mode="auto")

    s = (out.get("summary") or "").strip().lower()
    assert s.startswith("frontend"), "Frontend gate: summary must start with 'Frontend'"
    assert any(x in s for x in ["accessibility", "performance", "ui"]), \
        "Frontend gate: summary must contain accessibility OR performance OR UI"

def test_backend_summary_gate():
    master = {"summary": "", "skills": {"Core": ["Java", "SQL", "REST"]}, "projects": [], "experience": []}
    out = apply_intelligence(copy.deepcopy(master), role_family="Backend Developer", jd_text=BACKEND_JD, summary_mode="auto")

    s = (out.get("summary") or "").strip().lower()
    assert s.startswith("backend"), "Backend gate: summary must start with 'Backend'"

def test_fullstack_summary_gate():
    master = {"summary": "", "skills": {"Core": ["React", "TypeScript", "Java", "SQL"]}, "projects": [], "experience": []}
    out = apply_intelligence(copy.deepcopy(master), role_family="Full Stack Developer", jd_text=FULLSTACK_JD, summary_mode="auto")

    s = (out.get("summary") or "").strip().lower()
    assert s.startswith("full-stack") or s.startswith("full stack") or s.startswith("fullstack"), \
        "Fullstack gate: summary must start with 'Full-stack'"

def test_frontend_skills_first_bucket_gate():
    master = {
        "summary": "",
        "skills": {
            "Programming": ["Java", "Python"],
            "Web": ["ReactJS", "TypeScript", "CSS", "TailwindCSS"]
        },
        "projects": [],
        "experience": []
    }
    out = apply_intelligence(copy.deepcopy(master), role_family="Frontend Developer", jd_text=FRONTEND_JD, summary_mode="auto")

    first = first_skills_bucket_text(out.get("skills")).lower()
    assert any(k in first for k in ["react", "typescript", "css"]), \
        "Frontend gate: first skills bucket must contain React/TypeScript/CSS signal"