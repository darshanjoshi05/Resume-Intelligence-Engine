# learning_store.py
from __future__ import annotations
import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple

DATA_DIR = Path("data")
STORE_PATH = DATA_DIR / "learning_store.json"

def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _norm(s: str) -> str:
    t = (s or "").strip().lower()
    t = t.replace("•", " ").replace("·", " ").replace("—", "-").replace("–", "-")
    t = re.sub(r"\s+", " ", t).strip()
    return t

def _dedup(xs: List[str]) -> List[str]:
    out, seen = [], set()
    for x in xs:
        k = _norm(x)
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(k)
    return out

def load_store() -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not STORE_PATH.exists():
        d = {
            "version": 1,
            "updated_at": _now(),
            "roles": {},
            "global": {
                "term_stats": {},      # term -> {"count": int}
                "pair_stats": {},      # "a||b" -> count
                "concepts": {},        # concept -> {"members": [..], "count": int}
            },
        }
        STORE_PATH.write_text(json.dumps(d, indent=2), encoding="utf-8")
        return d

    try:
        return json.loads(STORE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {
            "version": 1,
            "updated_at": _now(),
            "roles": {},
            "global": {"term_stats": {}, "pair_stats": {}, "concepts": {}},
        }

def save_store(d: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    d["updated_at"] = _now()
    STORE_PATH.write_text(json.dumps(d, indent=2), encoding="utf-8")

# -----------------------------
# Seed concepts (hard-coded, then learns additions)
# -----------------------------
SEED_CONCEPTS = {
    "FRONTEND": {
        "state management": ["redux", "redux toolkit", "zustand", "mobx", "react query", "apollo client"],
        "ui testing": ["jest", "cypress", "playwright", "testing library"],
        "performance optimization": ["code splitting", "lazy loading", "lighthouse", "web vitals"],
        "css-in-js": ["styled components", "tailwindcss", "css modules", "emotion"],
        "build tools": ["webpack", "vite", "rollup"],
        "accessibility": ["wcag", "aria", "a11y"],
        "design systems": ["storybook", "figma", "adobe xd"],
        "api integration": ["rest", "graphql"],
        "frameworks": ["react", "next.js", "nextjs", "angular"],
        "pwa": ["progressive web app", "pwa", "service workers"],
    },
    "BACKEND": {
        "api": ["rest", "graphql"],
        "databases": ["sql", "postgresql", "mysql", "mongodb", "redis"],
        "microservices": ["microservices", "distributed systems"],
        "cloud": ["aws", "azure", "gcp"],
        "devops": ["docker", "kubernetes", "cicd", "jenkins", "github actions"],
    },
    "DATA": {
        "data analysis": ["pandas", "numpy", "tableau", "power bi"],
        "ml": ["scikit-learn", "machine learning"],
        "pipelines": ["etl", "data pipelines"],
        "databases": ["sql", "postgresql", "mysql"],
    },
}

def role_to_bucket(role_family: str) -> str:
    rf = (role_family or "").upper()
    if "FRONT" in rf or "REACT" in rf:
        return "FRONTEND"
    if "DATA" in rf or "ANALYST" in rf:
        return "DATA"
    if "JAVA" in rf or "BACK" in rf or "SOFTWARE" in rf:
        return "BACKEND"
    return "BACKEND"

def get_concepts_for_role(role_family: str, store: dict) -> Dict[str, List[str]]:
    bucket = role_to_bucket(role_family)
    out = {k: list(v) for k, v in (SEED_CONCEPTS.get(bucket, {}) or {}).items()}

    learned = (((store or {}).get("roles", {}) or {}).get(bucket, {}) or {}).get("concepts", {}) or {}
    for concept, obj in learned.items():
        members = obj.get("members", []) if isinstance(obj, dict) else []
        if members:
            base = out.get(concept, [])
            out[concept] = _dedup(base + members)

    # also include global concepts
    global_concepts = ((store or {}).get("global", {}) or {}).get("concepts", {}) or {}
    for concept, obj in global_concepts.items():
        members = obj.get("members", []) if isinstance(obj, dict) else []
        if members:
            base = out.get(concept, [])
            out[concept] = _dedup(base + members)

    return out

# -----------------------------
# Learning: term counts + co-occurrence pairs
# -----------------------------
def update_learning(role_family: str, terms: List[str]) -> None:
    store = load_store()
    bucket = role_to_bucket(role_family)

    store.setdefault("roles", {})
    store["roles"].setdefault(bucket, {"term_stats": {}, "pair_stats": {}, "concepts": {}})
    store.setdefault("global", {"term_stats": {}, "pair_stats": {}, "concepts": {}})

    clean_terms = _dedup([_norm(t) for t in (terms or []) if _norm(t)])
    if not clean_terms:
        return

    # term counts
    for scope in ("global",):
        ts = store[scope].setdefault("term_stats", {})
        for t in clean_terms:
            ts.setdefault(t, {"count": 0})
            ts[t]["count"] += 1

    rs = store["roles"][bucket].setdefault("term_stats", {})
    for t in clean_terms:
        rs.setdefault(t, {"count": 0})
        rs[t]["count"] += 1

    # pair counts (co-occurrence)
    def add_pairs(scope_obj: dict):
        ps = scope_obj.setdefault("pair_stats", {})
        for i in range(len(clean_terms)):
            for j in range(i + 1, len(clean_terms)):
                a, b = clean_terms[i], clean_terms[j]
                key = "||".join(sorted([a, b]))
                ps[key] = int(ps.get(key, 0)) + 1

    add_pairs(store["global"])
    add_pairs(store["roles"][bucket])

    # derive/expand concepts (simple, safe rules)
    _derive_concepts(bucket, store, clean_terms)

    save_store(store)

def _derive_concepts(bucket: str, store: dict, clean_terms: List[str]) -> None:
    """
    Practical learning, not academic:
    - If a JD contains a seed concept member pair frequently, add that member under concept
    - Also add common phrases if we see them co-occur with a concept cluster
    """
    concepts = store["roles"][bucket].setdefault("concepts", {})
    seed = SEED_CONCEPTS.get(bucket, {}) or {}

    # If multiple seed members appear in same JD, reinforce that concept
    for concept, members in seed.items():
        members_norm = {_norm(x) for x in members}
        hits = [t for t in clean_terms if t in members_norm]
        if len(hits) >= 2:
            concepts.setdefault(concept, {"members": [], "count": 0})
            concepts[concept]["count"] += 1
            # keep members list in case seeds are missing variants
            concepts[concept]["members"] = _dedup(concepts[concept].get("members", []) + hits)

    # Generic phrase capture (like "state management")
    # If phrase exists in clean_terms and co-occurs with multiple known members, add it as concept label
    # NOTE: we only allow a small whitelist of concept-like phrases to avoid junk.
    concept_like = {
        "state management",
        "performance optimization",
        "cross-browser compatibility",
        "responsive design",
        "accessibility",
        "ui testing",
        "build tools",
        "css-in-js",
        "design systems",
        "api integration",
    }
    for t in clean_terms:
        if t in concept_like:
            concepts.setdefault(t, {"members": [], "count": 0})
            concepts[t]["count"] += 1
