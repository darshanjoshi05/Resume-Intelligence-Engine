from __future__ import annotations
from typing import Dict, List, Any

def evaluate_quality(master: dict, jd_struct: dict, bridge_info: dict, selected_projects: List[dict]) -> dict:
    issues = []
    critical = []

    basics = master.get("basics", {}) if isinstance(master.get("basics", {}), dict) else {}

    name = master.get("name") or basics.get("name")
    email = master.get("email") or basics.get("email")
    phone = master.get("phone") or basics.get("phone")

    if not name:
        critical.append("Missing candidate name in master_profile.json.")
    if not email:
        issues.append("Missing email (add it for ATS + recruiter outreach).")
    if not phone:
        issues.append("Missing phone number (recommended).")

    matched = bridge_info.get("matched_skills", []) or []
    missing = bridge_info.get("missing_terms", []) or []
    if len(matched) == 0:
        issues.append("0 matched skills detected. Paste a fuller JD or improve your skill normalization.")
    if len(missing) > 25:
        issues.append("Very large missing list. JD likely contains noise or overly broad requirements.")

    if not selected_projects or len(selected_projects) == 0:
        issues.append("No projects selected for this JD. Consider adding tags to projects for better matching.")

    obj = master.get("objective") or master.get("summary") or ""
    if not obj or len(obj.strip()) < 40:
        issues.append("Objective/Summary is very short. Add a stronger baseline objective.")

    status = "PASS"
    if critical:
        status = "FAIL"
    elif issues:
        status = "WARN"

    score = 100
    score -= 25 * len(critical)
    score -= 8 * len(issues)
    score = max(0, min(100, score))

    return {
        "status": status,
        "score": score,
        "critical": critical,
        "issues": issues,
        "recommendation": (
            "Fix critical items before generating." if status == "FAIL"
            else "You can generate, but review warnings." if status == "WARN"
            else "Looks good."
        ),
    }
