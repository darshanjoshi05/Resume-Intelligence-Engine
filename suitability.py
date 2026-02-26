# suitability.py
from __future__ import annotations
from typing import Dict, List, Tuple
import re

# -----------------------------
# Thresholds (Option D)
# -----------------------------
STRONG_THRESHOLD = 70.0
PARTIAL_THRESHOLD = 45.0

def decide_verdict(match_score: float) -> str:
    """
    Returns: STRONG | PARTIAL | LOW
    """
    try:
        s = float(match_score)
    except Exception:
        s = 0.0

    if s >= STRONG_THRESHOLD:
        return "STRONG"
    if s >= PARTIAL_THRESHOLD:
        return "PARTIAL"
    return "LOW"


# -----------------------------
# Master profile skill helpers
# -----------------------------
def _flatten_master_skills(master: dict) -> List[str]:
    """
    Returns a normalized list of skills/tags from master_profile.json.
    Supports:
      - master["skills"][category] = [..]
      - projects[].tags = [..]
    """
    out: List[str] = []

    skills = master.get("skills") or {}
    if isinstance(skills, dict):
        for _, items in skills.items():
            if isinstance(items, list):
                out.extend([str(x) for x in items if str(x).strip()])
            else:
                if str(items).strip():
                    out.append(str(items))

    # project tags also matter
    for pr in master.get("projects", []) or []:
        tags = pr.get("tags", [])
        if isinstance(tags, list):
            out.extend([str(x) for x in tags if str(x).strip()])

    # normalize
    normed = []
    seen = set()
    for x in out:
        k = re.sub(r"\s+", " ", str(x).strip().lower())
        if not k:
            continue
        if k in seen:
            continue
        seen.add(k)
        normed.append(k)
    return normed


def infer_candidate_lanes(master: dict) -> List[str]:
    """
    Detect the candidate's strongest lanes based on skill signals.
    Returns a ranked list of lane keys.
    """
    s = set(_flatten_master_skills(master))

    def has_any(*terms):
        return any(t.lower() in s for t in terms)

    lanes: List[Tuple[str, int]] = []

    # Data / ML
    ml_score = 0
    if has_any("python"): ml_score += 2
    if has_any("pandas", "numpy", "scikit-learn", "machine learning"): ml_score += 3
    if has_any("data visualization", "power bi", "tableau"): ml_score += 1
    if ml_score:
        lanes.append(("DATA_ML", ml_score))

    # Backend
    be_score = 0
    if has_any("java", ".net", "c#", "python"): be_score += 2
    if has_any("sql", "postgresql", "mysql", "mongodb"): be_score += 2
    if has_any("rest concepts", "api", "microservices"): be_score += 2
    if be_score:
        lanes.append(("BACKEND", be_score))

    # Frontend
    fe_score = 0
    if has_any("reactjs", "react", "javascript", "typescript", "html", "css"): fe_score += 4
    if fe_score:
        lanes.append(("FRONTEND", fe_score))

    # Security
    sec_score = 0
    if has_any("security", "gdb", "buffer overflow"): sec_score += 4
    if sec_score:
        lanes.append(("SECURITY", sec_score))

    # Generic SWE
    swe_score = 0
    if has_any("oop", "algorithms", "data structures", "git"): swe_score += 2
    if swe_score:
        lanes.append(("GENERAL_SWE", swe_score))

    lanes.sort(key=lambda x: x[1], reverse=True)
    return [k for k, _ in lanes] or ["GENERAL_SWE"]


def suggested_roles_from_lanes(lanes: List[str]) -> List[str]:
    """
    Turn lane keys into human-friendly suggested roles.
    """
    MAP = {
        "DATA_ML": ["Data Analyst", "ML Engineer (Junior)", "Data Engineer (Entry)"],
        "BACKEND": ["Backend Developer (Junior)", "Python Developer", "Java Developer (Junior)"],
        "FRONTEND": ["Frontend Developer (React)", "Full-Stack Developer (Junior)"],
        "SECURITY": ["Security Analyst (Entry)", "Application Security (Intern/Junior)"],
        "GENERAL_SWE": ["Software Engineer (Entry)", "Application Developer (Junior)"],
    }
    out: List[str] = []
    for k in lanes:
        out.extend(MAP.get(k, []))
    # dedup keep order
    seen = set()
    final = []
    for r in out:
        if r.lower() in seen:
            continue
        seen.add(r.lower())
        final.append(r)
    return final[:6]


def learning_plan_from_missing(missing_terms: List[str], limit: int = 12) -> List[str]:
    """
    Keep it actionable and not too long.
    """
    clean = []
    seen = set()
    for t in missing_terms or []:
        k = re.sub(r"\s+", " ", str(t).strip())
        if not k:
            continue
        lk = k.lower()
        if lk in seen:
            continue
        seen.add(lk)
        clean.append(k)
    return clean[:limit]
