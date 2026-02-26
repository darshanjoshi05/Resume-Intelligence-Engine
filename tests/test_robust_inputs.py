import copy
import pytest
from resume_intel import apply_intelligence
from tests._helpers import FRONTEND_JD

@pytest.mark.parametrize("master", [
    {"summary": "", "skills": {}, "projects": [], "experience": []},
    {"summary": None, "skills": None, "projects": None, "experience": None},
    {"skills": {"Core": ["React"]}},  # missing keys
    {"summary": "", "skills": {"Core": ["React"]}, "projects": [{}], "experience": [{}]},
])
def test_does_not_crash_on_messy_inputs(master):
    out = apply_intelligence(copy.deepcopy(master), role_family="Frontend Developer", jd_text=FRONTEND_JD, summary_mode="auto")
    assert isinstance(out, dict)
    # Must always provide these keys to protect UI/backend
    assert "summary" in out
    assert "skills" in out
    assert "projects" in out
    assert "experience" in out