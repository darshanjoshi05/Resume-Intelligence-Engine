import copy
from resume_intel import apply_intelligence
from tests._helpers import FRONTEND_JD, all_text, BAD_LEAK_TOKENS

def test_output_schema_minimum_types():
    master = {
        "summary": "",
        "skills": {"Core": ["React", "TypeScript", "CSS"]},
        "projects": [],
        "experience": [],
    }
    out = apply_intelligence(copy.deepcopy(master), role_family="Frontend Developer", jd_text=FRONTEND_JD, summary_mode="auto")

    assert isinstance(out, dict)
    assert "summary" in out and isinstance(out["summary"], str)
    assert "skills" in out and isinstance(out["skills"], (dict, list))
    assert "projects" in out and isinstance(out["projects"], list)
    assert "experience" in out and isinstance(out["experience"], list)

def test_scorecard_contract():
    master = {"summary": "", "skills": {"Core": ["React"]}, "projects": [], "experience": []}
    out = apply_intelligence(copy.deepcopy(master), role_family="Frontend Developer", jd_text=FRONTEND_JD, summary_mode="auto")

    sc = out.get("_scorecard")
    assert isinstance(sc, dict)

    required = [
        "archetype","alignment_coverage","missing_count",
        "skills_count","projects_count","project_bullets_count"
    ]
    for k in required:
        assert k in sc

def test_no_debug_leaks_anywhere():
    master = {
        "summary": "",
        "skills": {"Core": ["React", "TypeScript", "CSS"]},
        "projects": [{"name":"X","tech":"React","bullets":["Did thing."]}],
        "experience": [{"title":"Y","org":"Z","bullets":["Did work."]}],
    }
    out = apply_intelligence(copy.deepcopy(master), role_family="Frontend Developer", jd_text=FRONTEND_JD, summary_mode="auto")
    text = all_text(out).lower()

    for tok in BAD_LEAK_TOKENS:
        assert tok.lower() not in text, f"Leak token found: {tok}"