import copy
from resume_intel import apply_intelligence
from tests._helpers import FRONTEND_JD

def test_summary_length_and_comma_spam():
    master = {"summary": "", "skills": {"Core": ["React", "TypeScript", "CSS"]}, "projects": [], "experience": []}
    out = apply_intelligence(copy.deepcopy(master), role_family="Frontend Developer", jd_text=FRONTEND_JD, summary_mode="auto")

    s = out.get("summary") or ""
    assert len(s) <= 450, "Summary too long; likely template bloat"
    assert s.count(",") <= 8, "Comma spam; hurts readability/ATS"

def test_no_empty_bullets():
    master = {
        "summary": "",
        "skills": {"Core": ["React"]},
        "projects": [{"name":"P","tech":"React","bullets":["", "   ", None, "Built UI."]}],
        "experience": [{"title":"E","org":"O","bullets":["", "Shipped feature."]}],
    }
    out = apply_intelligence(copy.deepcopy(master), role_family="Frontend Developer", jd_text=FRONTEND_JD, summary_mode="auto")

    for p in out.get("projects", []):
        if isinstance(p, dict):
            bullets = p.get("bullets") or []
            assert all((b or "").strip() for b in bullets), "Empty project bullet leaked into output"

    for e in out.get("experience", []):
        if isinstance(e, dict):
            bullets = e.get("bullets") or []
            assert all((b or "").strip() for b in bullets), "Empty experience bullet leaked into output"