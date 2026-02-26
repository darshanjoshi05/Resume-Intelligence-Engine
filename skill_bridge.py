# skill_bridge.py
from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Any, Dict, List

from matcher import match_terms

ALIASES_PATH = Path("data") / "skill_aliases_seed.json"
LEARNED_PATH = Path("data") / "learned_skills.json"  # kept for backward compat

_BLACKLIST = {
    "experience", "years", "year", "months", "month", "skills", "skill", "knowledge",
    "responsibilities", "requirements", "preferred", "plus", "bonus", "ability",
    "strong", "excellent", "communication", "team", "teams", "work", "working",
    "role", "position", "job", "candidate", "qualifications"
}

_CANON = {
    "react.js": "react",
    "reactjs": "react",
    "node.js": "node",
    "nodejs": "node",
    "postgres": "postgresql",
    "mssql": "sql server",
    "ms sql": "sql server",
    "restful": "rest",
    "apis": "api",
    "k8s": "kubernetes",
    "dotnet": ".net",
    "nextjs": "next.js",
    "redux toolkit": "redux toolkit",
}

TECH_TOKEN = re.compile(r"\b[a-zA-Z][a-zA-Z0-9\.\+\-#/]{1,}\b")

def _norm(s: str) -> str:
    t = str(s or "").strip().lower()
    t = t.replace("•", " ").replace("·", " ").replace("—", "-")
    t = re.sub(r"\s+", " ", t).strip()
    return _CANON.get(t, t)

def load_aliases() -> dict:
    if not ALIASES_PATH.exists():
        return {}
    try:
        return json.loads(ALIASES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

def load_learned_terms() -> set[str]:
    # legacy vocabulary support (doesn't drive learning anymore)
    if not LEARNED_PATH.exists():
        return set()
    try:
        data = json.loads(LEARNED_PATH.read_text(encoding="utf-8"))
        skills = data.get("skills", {}) or {}
        return {_norm(k) for k in skills.keys() if k}
    except Exception:
        return set()

def flatten_master_skills(master_profile: dict) -> List[str]:
    skills: List[str] = []
    skill_groups = master_profile.get("skills", {}) or {}
    if isinstance(skill_groups, dict):
        for _, items in skill_groups.items():
            if isinstance(items, list):
                skills.extend([str(s).strip() for s in items if str(s).strip()])
            else:
                if str(items).strip():
                    skills.append(str(items).strip())
    elif isinstance(skill_groups, list):
        skills.extend([str(x).strip() for x in skill_groups if str(x).strip()])
    return skills

def _is_candidate_term(term: str) -> bool:
    t = _norm(term)
    if not t or t in _BLACKLIST:
        return False
    if len(t) < 3:
        return False
    if all(ch.isdigit() for ch in t):
        return False
    if len(t) > 60:
        return False
    if re.search(r"\byears?\b|\bmonths?\b", t):
        return False
    return True

def extract_jd_keywords(jd: str) -> List[str]:
    """
    Fallback if jd_struct isn't provided.
    """
    found = []
    for tok in TECH_TOKEN.findall(jd or ""):
        n = _norm(tok)
        if _is_candidate_term(n):
            found.append(n)
    # keep unique
    out, seen = [], set()
    for x in found:
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out[:120]

def _collect_jd_terms(jd: str, jd_struct: dict | None) -> List[str]:
    if jd_struct:
        terms = []
        for k in (jd_struct.get("jd_signals", []) or []):
            terms.append(k)
        for k in (jd_struct.get("hard_skills", []) or []):
            terms.append(k)
        for k in (jd_struct.get("role_signals", []) or []):
            terms.append(k)
        for k in (jd_struct.get("keywords", []) or []):
            terms.append(k)
        clean = []
        for x in terms:
            if _is_candidate_term(x):
                clean.append(_norm(x))
        # dedup
        out, seen = [], set()
        for x in clean:
            if x in seen:
                continue
            seen.add(x)
            out.append(x)
        return out[:120]
    return extract_jd_keywords(jd)

def smart_bridge_skills(master_profile: dict, jd: str, jd_struct: dict | None = None, role_family: str = "") -> dict:
    """
    Upgraded matching:
      - exact matches
      - concept matches (state management -> redux/zustand/mobx)
      - partial matches (lightweight fuzzy)
    """
    master_skills = flatten_master_skills(master_profile)
    aliases = load_aliases()

    jd_terms = _collect_jd_terms(jd, jd_struct)

    # 1) Matching engine (exact + concept + partial)
    m = match_terms(jd_terms, master_skills, role_family or "")

    matched = sorted({x for x in (m.get("matched") or []) if x})
    concept = m.get("concept") or []
    partial = m.get("partial") or []
    missing = m.get("missing") or []

    # 2) Alias-based bridges (kept)
    bridges_out = []
    for master_skill, terms in (aliases or {}).items():
        if master_skill not in master_skills:
            continue
        terms_list = [terms] if isinstance(terms, str) else list(terms or [])
        for alias_term in terms_list:
            if _norm(alias_term) in set(_norm(x) for x in jd_terms):
                bridges_out.append({"from": master_skill, "to": alias_term, "phrase": f"{master_skill} (aligned with {alias_term})"})

    # 3) Add partial matches as SAFE bridges (not direct claims)
    for jt, p, sc in partial:
        bridges_out.append({"from": p, "to": jt, "phrase": f"{p} (partially aligned with {jt})"})

    # 4) Add concept matches as SAFE bridges
    for expl in concept:
        bridges_out.append({"from": "concept", "to": expl, "phrase": f"Concept match: {expl}"})

    # dedup bridges by phrase
    seen = set()
    final_bridges = []
    for b in bridges_out:
        phr = (b.get("phrase") or "").strip().lower()
        if not phr or phr in seen:
            continue
        seen.add(phr)
        final_bridges.append(b)

    return {
        "matched_skills": matched,
        "bridges": final_bridges,
        "missing_terms": missing[:30],
        "jd_terms_count": len(jd_terms),
    }
