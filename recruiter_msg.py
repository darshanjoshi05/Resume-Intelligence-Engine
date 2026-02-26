# recruiter_msg.py
from __future__ import annotations
import re
from typing import List

def _norm(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    return s

def build_recruiter_message(
    master: dict,
    company: str,
    role_title: str,
    role_family: str,
    match_score: float,
    matched_skills: List[str],
    selected_projects: List[dict],
) -> str:
    name = master.get("name") or master.get("basics", {}).get("name") or "Darshan"
    name = _norm(name)

    # pick 2 strong signals
    skills = [s for s in (matched_skills or []) if s and len(str(s)) <= 24]
    skills = list(dict.fromkeys(skills))[:3]

    proj_names = [p.get("name", "") for p in (selected_projects or []) if p.get("name")]
    proj_bit = ""
    if proj_names:
        proj_bit = f"Relevant project work: {', '.join(proj_names[:2])}."

    # tiers
    if match_score >= 80:
        opener = f"Hi — I’m {name}. I applied for the {role_title} role at {company}."
        value = "I can contribute quickly with hands-on delivery, clean documentation, and strong fundamentals."
    elif match_score >= 60:
        opener = f"Hi — I’m {name}. I’m applying for the {role_title} role at {company}."
        value = "My background aligns well with the core requirements, and I’m comfortable ramping fast on your stack."
    else:
        opener = f"Hi — I’m {name}. I’m interested in the {role_title} role at {company}."
        value = "I bring strong fundamentals and proven project execution, and I’d love to contribute to the team."

    skill_bit = ""
    if skills:
        skill_bit = f"Strong fit areas: {', '.join(skills[:3])}."

    ask = "If you’re the right person to speak with, I’d appreciate a quick chat to confirm fit and next steps."

    msg = " ".join([opener, value, skill_bit, proj_bit, ask])
    msg = re.sub(r"\s+", " ", msg).strip()
    return msg
