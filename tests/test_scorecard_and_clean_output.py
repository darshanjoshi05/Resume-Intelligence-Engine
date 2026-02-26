import copy
from resume_intel import apply_intelligence

FRONTEND_JD = """
Frontend Developer. React, Next.js, Angular. TailwindCSS, Styled Components.
Redux Toolkit, Zustand, MobX. Lighthouse. WCAG 2.1. Jest, Cypress, Playwright.
Webpack, Vite, Rollup. Storybook, Figma.
"""

def _all_text(out: dict) -> str:
    parts = []
    parts.append(str(out.get("summary") or ""))

    skills = out.get("skills") or {}
    if isinstance(skills, dict):
        for _, items in skills.items():
            if isinstance(items, list):
                parts.extend([str(x) for x in items])
            else:
                parts.append(str(items))

    for p in (out.get("projects") or []):
        if isinstance(p, dict):
            parts.append(str(p.get("name", "")))
            parts.append(str(p.get("tech", "")))
            parts.extend([str(b) for b in (p.get("bullets") or [])])

    for e in (out.get("experience") or []):
        if isinstance(e, dict):
            parts.append(str(e.get("title", "")))
            parts.append(str(e.get("org", "")))
            parts.extend([str(b) for b in (e.get("bullets") or [])])

    return "\n".join(parts)

def test_scorecard_exists_and_has_expected_keys():
    master = {"summary": "", "skills": {"Core": ["React", "Next.js", "TypeScript"]}, "projects": [], "experience": []}
    out = apply_intelligence(copy.deepcopy(master), role_family="Frontend Developer", jd_text=FRONTEND_JD, summary_mode="auto")

    sc = out.get("_scorecard")
    assert isinstance(sc, dict)
    for k in ["archetype","alignment_coverage","missing_count","summary_commas","skills_count","projects_count","project_bullets_count","leak_detected"]:
        assert k in sc

def test_clean_output_no_aligned_leak_anywhere():
    master = {
        "summary": "",
        "skills": {"Core": ["React", "Next.js", "TypeScript", "Redux Toolkit", "TailwindCSS"]},
        "projects": [
            {"name": "Classroom Behaviour Detection", "tech": "Python", "bullets": ["Built pipelines for preprocessing and visualization."]},
            {"name": "Buffer Overflow Vulnerability Analysis", "tech": "C, GDB", "bullets": ["Diagnosed stack behavior and exploit vectors."]},
        ],
        "experience": [],
    }
    out = apply_intelligence(copy.deepcopy(master), role_family="Frontend Developer", jd_text=FRONTEND_JD, summary_mode="auto")

    text = _all_text(out).lower()
    assert "aligned:" not in text
    assert "(aligned:" not in text
