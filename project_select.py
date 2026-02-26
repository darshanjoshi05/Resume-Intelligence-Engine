# project_select.py
from __future__ import annotations
import re
from typing import List, Dict, Tuple

def _norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"\s+", " ", s)
    s = s.strip(" .,:;|/\\")
    return s

def _tokenize(text: str) -> set:
    if not text:
        return set()
    text = _norm(text)
    toks = re.findall(r"[a-z0-9\.\+#/]+", text)
    return set(toks)

def score_project(project: dict, jd_terms: List[str]) -> float:
    """
    Score by overlap:
      tags = strong signal
      bullets = medium signal
    """
    jd = set(_norm(x) for x in jd_terms if x)
    if not jd:
        return 0.0

    tags = project.get("tags", []) or []
    bullets = project.get("bullets", []) or []

    tag_terms = set(_norm(x) for x in tags if x)
    bullet_terms = set()
    for b in bullets:
        bullet_terms |= _tokenize(b)

    # weighted overlap
    tag_hit = len(jd & tag_terms)
    bullet_hit = len(jd & bullet_terms)

    return (3.0 * tag_hit) + (1.0 * bullet_hit)

def pick_projects(master_profile: dict, jd_struct: dict) -> Tuple[List[dict], dict]:
    """
    Returns (selected_projects, debug)
    Default:
      - top 2
      - top 3 if 3rd is close and strong
    """
    projects = master_profile.get("projects", []) or []
    jd_terms = (jd_struct.get("keywords", []) or [])
    jd_must = jd_struct.get("must_have_skills", []) or []
    jd_terms = list(dict.fromkeys([*jd_must, *jd_terms]))  # keep order-ish

    scored = []
    for p in projects:
        s = score_project(p, jd_terms)
        scored.append((s, p))

    scored.sort(key=lambda x: x[0], reverse=True)

    # Always keep at least 1 if any exist
    top = [p for s, p in scored if s > 0]
    if not top and projects:
        top = [projects[0]]

    selected = top[:2]

    # optional 3rd project if it’s meaningful
    if len(top) >= 3:
        s2 = score_project(top[1], jd_terms) if len(top) > 1 else 0.0
        s3 = score_project(top[2], jd_terms)
        # add 3rd if strong and close to #2
        if s3 >= 3.0 and (s2 == 0.0 or s3 >= 0.70 * s2):
            selected = top[:3]

    debug = {
        "scored": [
            {"name": p.get("name", ""), "score": float(s)}
            for s, p in scored[:10]
        ],
        "selected": [p.get("name", "") for p in selected],
        "rule": "Top 2 (Top 3 if #3 is strong & close)",
    }
    return selected, debug
