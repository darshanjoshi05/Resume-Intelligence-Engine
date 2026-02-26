from pathlib import Path

def ats_health_report(master: dict, blocks: dict) -> dict:
    issues = []
    basics = master.get("basics", {}) if isinstance(master.get("basics", {}), dict) else {}

    # contact check
    def getv(k: str) -> str:
        return str(master.get(k) or basics.get(k) or "").strip()

    for key in ["name", "email", "phone"]:
        if not getv(key):
            issues.append(f"Missing {key} in profile.")

    # skills section check
    skill_lines = blocks.get("skills_lines", []) or []
    if len(skill_lines) < 2:
        issues.append("Skills section looks too small. Add more grouped skills in profile.")

    # summary length check
    summary = (blocks.get("summary") or "")
    if len(summary) < 40:
        issues.append("Summary is too short. Add 1–2 stronger lines.")

    score = 100 - min(60, len(issues) * 15)
    return {"score": score, "issues": issues}
