import copy
from resume_intel import apply_intelligence
from tests._helpers import FRONTEND_JD, stable_dump

def test_same_input_same_output():
    master = {"summary": "", "skills": {"Core": ["React", "TypeScript", "CSS"]}, "projects": [], "experience": []}
    a = apply_intelligence(copy.deepcopy(master), role_family="Frontend Developer", jd_text=FRONTEND_JD, summary_mode="auto")
    b = apply_intelligence(copy.deepcopy(master), role_family="Frontend Developer", jd_text=FRONTEND_JD, summary_mode="auto")
    assert stable_dump(a) == stable_dump(b)