# learn_jd.py
from __future__ import annotations

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Tuple

DATA_DIR = Path("data")
STORE_PATH = DATA_DIR / "learned_store.json"

# -----------------------------
# Canonicalization (keep stable)
# -----------------------------
_CANON = {
    "reactjs": "react",
    "react.js": "react",
    "nodejs": "node",
    "node.js": "node",
    "nextjs": "next.js",
    "angularjs": "angular",
    "restful": "rest",
    "apis": "api",
    "ci/cd": "cicd",
    "ci-cd": "cicd",
    "k8s": "kubernetes",
    "ts": "typescript",
    "js": "javascript",
    "webpack.js": "webpack",
}

_TECH_TOKEN = re.compile(r"\b[a-zA-Z][a-zA-Z0-9\.\+\-#/]{1,}\b")

# Keep this list small; it’s only for blocking obvious junk.
_NOISE = {
    "benefits", "insurance", "salary", "compensation", "equal opportunity", "eeo",
    "requirements", "responsibilities", "preferred", "qualification", "qualifications",
    "experience", "years", "year", "months", "month", "team", "teams", "communication",
    "stakeholders", "meetings", "coordinate", "about", "role", "company",
}


def _norm(t: str) -> str:
    s = (t or "").strip().lower()
    s = s.replace("—", "-").replace("–", "-").replace("•", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return _CANON.get(s, s)


def _is_noise_term(t: str) -> bool:
    s = _norm(t)
    if not s or len(s) <= 1:
        return True
    if s in _NOISE:
        return True
    if "http://" in s or "https://" in s or "www." in s:
        return True
    if re.search(r"\b[a-z0-9\-]+\.(com|org|net|io|ai|edu)\b", s):
        return True
    # reject sentence-like fragments
    if len(s) > 60 and " " in s and not re.search(r"[+#./]", s):
        return True
    return False


# -----------------------------
# Concept groups (starter pack)
# Use this for grouping + partial matching.
# You can expand safely without breaking schema.
# -----------------------------
CONCEPT_GROUPS: Dict[str, List[str]] = {
    # Frontend: state management & data fetching
    "state_management": ["redux", "redux toolkit", "zustand", "mobx", "context api"],
    "data_fetching_cache": ["react query", "tanstack query", "apollo client", "graphql", "swr"],

    # Frontend: frameworks
    "frontend_frameworks": ["react", "next.js", "angular", "vue"],

    # Frontend: testing
    "ui_testing": ["jest", "cypress", "playwright", "testing library"],

    # Frontend: perf
    "performance_optimization": ["code splitting", "lazy loading", "lighthouse", "web vitals"],

    # Frontend: styling / design systems
    "css_in_js": ["styled components", "tailwindcss", "css-in-js", "storybook"],
    "design_tools": ["figma", "adobe xd"],

    # Accessibility
    "accessibility": ["wcag", "wcag 2.1", "aria", "a11y"],

    # Build tools
    "build_tools": ["webpack", "vite", "rollup"],

    # PWA
    "pwa": ["pwa", "service worker", "progressive web app"],
}


def concept_of(term: str) -> str | None:
    t = _norm(term)
    for k, items in CONCEPT_GROUPS.items():
        if t in {_norm(x) for x in items}:
            return k
    return None


def expand_concepts(terms: List[str]) -> List[str]:
    """
    If JD mentions a concept-level phrase like "state management",
    expand it into concrete tools (redux/zustand/mobx) as "targets".
    """
    out: List[str] = []
    seen = set()

    norm_terms = [_norm(x) for x in (terms or []) if x]
    for t in norm_terms:
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(t)

        # Concept triggers (phrases that represent groups)
        if t in {"state management", "client-side state", "client side state"}:
            out.extend([_norm(x) for x in CONCEPT_GROUPS.get("state_management", [])])
        if t in {"api caching", "caching", "data fetching"}:
            out.extend([_norm(x) for x in CONCEPT_GROUPS.get("data_fetching_cache", [])])
        if t in {"ui testing", "test automation", "automated ui testing"}:
            out.extend([_norm(x) for x in CONCEPT_GROUPS.get("ui_testing", [])])
        if t in {"performance", "performance optimization"}:
            out.extend([_norm(x) for x in CONCEPT_GROUPS.get("performance_optimization", [])])

    # final dedup keep order
    final: List[str] = []
    seen2 = set()
    for x in out:
        if x and x not in seen2 and not _is_noise_term(x):
            seen2.add(x)
            final.append(x)
    return final


# -----------------------------
# Store I/O
# -----------------------------
def _default_store() -> dict:
    return {
        "meta": {
            "version": 1,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        },
        "terms": {
            # term -> {count:int, last_seen:str, roles:{role_family:count}}
        },
        "roles": {
            # role_family -> {count:int, last_seen:str}
        },
    }


def load_store() -> dict:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not STORE_PATH.exists():
        s = _default_store()
        STORE_PATH.write_text(json.dumps(s, indent=2), encoding="utf-8")
        return s
    try:
        data = json.loads(STORE_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return _default_store()
        data.setdefault("meta", {})
        data.setdefault("terms", {})
        data.setdefault("roles", {})
        return data
    except Exception:
        return _default_store()


def save_store(store: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    store = store or _default_store()
    store.setdefault("meta", {})
    store["meta"]["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    STORE_PATH.write_text(json.dumps(store, indent=2), encoding="utf-8")


# -----------------------------
# Learning API
# -----------------------------
def learn_terms(terms: List[str], role_family: str = "") -> None:
    """
    Persist terms learned from JD signals.
    This does NOT auto-inject into resumes; it just stores counts/weights.
    """
    store = load_store()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    role_family = (role_family or "").strip().upper() or "UNKNOWN"
    store["roles"].setdefault(role_family, {"count": 0, "last_seen": ""})
    store["roles"][role_family]["count"] = int(store["roles"][role_family].get("count", 0)) + 1
    store["roles"][role_family]["last_seen"] = now

    # Expand concept triggers (state management -> redux, zustand, mobx)
    expanded = expand_concepts([str(x) for x in (terms or []) if str(x).strip()])

    for raw in expanded:
        t = _norm(raw)
        if _is_noise_term(t):
            continue

        store["terms"].setdefault(t, {"count": 0, "last_seen": "", "roles": {}})
        store["terms"][t]["count"] = int(store["terms"][t].get("count", 0)) + 1
        store["terms"][t]["last_seen"] = now
        roles = store["terms"][t].setdefault("roles", {})
        roles[role_family] = int(roles.get(role_family, 0)) + 1

    save_store(store)


def term_weight(term: str, role_family: str = "") -> float:
    """
    Weight grows with:
      - global frequency
      - role-family frequency (stronger)
    Used to prioritize skills/projects/summary words.
    """
    t = _norm(term)
    if _is_noise_term(t):
        return 0.0

    store = load_store()
    rec = (store.get("terms") or {}).get(t)
    if not isinstance(rec, dict):
        return 0.0

    g = float(rec.get("count", 0) or 0)
    rf = (role_family or "").strip().upper() or "UNKNOWN"
    r = float(((rec.get("roles") or {}) or {}).get(rf, 0) or 0)

    # Simple stable formula:
    # role-hit matters more than global
    return (1.0 * g) + (2.5 * r)


def top_terms(role_family: str = "", limit: int = 20) -> List[str]:
    store = load_store()
    terms = store.get("terms") or {}
    rf = (role_family or "").strip().upper() or "UNKNOWN"

    scored: List[Tuple[float, str]] = []
    for t, rec in terms.items():
        if not isinstance(rec, dict):
            continue
        w = term_weight(t, rf)
        if w > 0:
            scored.append((w, t))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [t for _, t in scored[: max(0, int(limit))]]
