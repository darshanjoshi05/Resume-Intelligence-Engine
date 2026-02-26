# resume_intel.py
from __future__ import annotations

import re
import copy
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Iterable, Set

try:
    # Optional: JD learning store (can be deleted without breaking the app)
    from learn_jd import term_weight, top_terms  # type: ignore
except Exception:
    def term_weight(term: str, role_family: str = "") -> float:  # type: ignore
        return 0.0

    def top_terms(role_family: str = "", limit: int = 20) -> list[str]:  # type: ignore
        return []


DATA_DIR = Path("data")
SETTINGS_PATH = DATA_DIR / "settings.json"


def _load_settings() -> dict:
    """Tiny settings loader with safe defaults. No app imports."""
    try:
        if SETTINGS_PATH.exists():
            import json as _json
            data = _json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}


def _summary_mode(settings: dict) -> str:
    out = (settings.get("output") or {}) if isinstance(settings.get("output"), dict) else {}
    mode = str(out.get("summary_mode") or "dynamic_with_override").strip().lower()
    if mode not in {"dynamic_with_override", "always_dynamic", "always_custom"}:
        return "dynamic_with_override"
    return mode


DEFAULT_MIN_WORDS = 420

_VERB_MAP = {
    r"\bdesigned\b": "engineered",
    r"\bimplemented\b": "built",
    r"\bdeveloped\b": "built",
    r"\bcreated\b": "built",
    r"\bmade\b": "built",
    r"\bworked on\b": "delivered",
    r"\bhelped\b": "supported",
    r"\bused\b": "leveraged",
    r"\butilized\b": "leveraged",
    r"\btested\b": "validated",
    r"\boptimized\b": "tuned",
    r"\bimproved\b": "strengthened",
    r"\banalyzed\b": "evaluated",
    r"\bdebugged\b": "diagnosed",
    r"\bcollaborated\b": "partnered",
    r"\bpresented\b": "communicated",
}

_SAFE_ENGINEERING_PHRASES = [
    "Validated outputs with basic testing and structured debugging using repeatable runs.",
    "Documented decisions and tradeoffs to keep implementation maintainable.",
    "Focused on usability and accessibility with attention to performance hygiene where applicable.",
]

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9\.\+#/]{1,}")

_NOISE = {
    "benefits", "equal", "opportunity", "eeo", "insurance", "salary", "accommodation",
    "responsibilities", "requirements", "preferred", "about", "role", "team", "company",
    "years", "experience", "skills", "job", "work", "ability", "strong", "communication",
    "stakeholders", "documentation", "meetings", "coordinate",
}


def _norm(s: str) -> str:
    s = (s or "").strip()
    s = s.replace("\u2013", "-").replace("\u2014", "-")
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _norm_low(s: str) -> str:
    return _norm(s).lower()


def _dedup_keep(xs: List[str]) -> List[str]:
    out, seen = [], set()
    for x in xs:
        k = _norm_low(x)
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(_norm(x))
    return out


# ============================================================
# Tech-term whitelist filter (before tech_blob)
# ============================================================
_TECH_WHITELIST: Set[str] = {
    # Languages
    "javascript", "typescript", "python", "java", "c#", "sql",
    # Frontend
    "react", "next.js", "angular", "html", "css", "tailwindcss", "styled-components",
    # State
    "redux", "redux toolkit", "zustand", "mobx",
    # Backend
    "node.js", "express", "nest.js", "spring boot", ".net", "asp.net",
    # APIs
    "rest", "graphql",
    # Testing
    "jest", "cypress", "playwright",
    # Build
    "webpack", "vite", "rollup",
    # DB
    "postgresql", "mysql", "mongodb", "redis",
    # Quality
    "lighthouse", "wcag", "accessibility",
}

_TECH_ALIASES = {
    "reactjs": "react",
    "react.js": "react",
    "next": "next.js",
    "nextjs": "next.js",
    "node": "node.js",
    "nodejs": "node.js",
    "tailwind": "tailwindcss",
    "rtk": "redux toolkit",
    "rest api": "rest",
    "restful": "rest",
}


def _norm_skill(s: str) -> str:
    s = (s or "").strip().lower()
    s = s.replace("\u2013", "-").replace("\u2014", "-")
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"^[\W_]+|[\W_]+$", "", s)  # trim punctuation
    return s.strip()


def filter_tech_terms(terms: Iterable[str], whitelist: Optional[Set[str]] = None) -> List[str]:
    wl = whitelist or _TECH_WHITELIST
    out: List[str] = []
    seen = set()

    for raw in (terms or []):
        s = _norm_skill(str(raw))
        if not s:
            continue
        s = _TECH_ALIASES.get(s, s)
        if s in wl and s not in seen:
            out.append(s)
            seen.add(s)

    return out


def _extract_jd_terms(jd_text: str, jd_struct: Optional[dict]) -> List[str]:
    terms: List[str] = []

    if isinstance(jd_struct, dict):
        # prefer tech-only signals if available
        if isinstance(jd_struct.get("jd_signals"), list):
            terms += [str(x) for x in (jd_struct.get("jd_signals") or []) if str(x).strip()]
        else:
            for k in ("must_have_skills", "tools_tech", "nice_to_have_skills", "keywords"):
                arr = jd_struct.get(k) or []
                if isinstance(arr, list):
                    terms += [str(x) for x in arr if str(x).strip()]

    if len(terms) < 10:
        toks = _TOKEN_RE.findall(jd_text or "")
        for t in toks:
            tl = t.lower()
            if tl in _NOISE:
                continue
            if len(t) <= 2:
                continue
            terms.append(t)

    cleaned = []
    for t in terms:
        t = _norm(t)
        if not t:
            continue
        tl = t.lower()
        if tl in _NOISE:
            continue
        cleaned.append(t)

    cleaned = _dedup_keep(cleaned)
    return cleaned[:80]


def _strengthen_verbs(line: str) -> str:
    s = _norm(line)
    if not s:
        return s
    out = s
    for pat, rep in _VERB_MAP.items():
        out = re.sub(pat, rep, out, flags=re.IGNORECASE)
    out = out[0].upper() + out[1:] if out else out
    return out


# ============================================================
# Summary rewriting — tone by level + lane + learned terms
# ============================================================
def _detect_level(jd_text: str) -> str:
    t = (jd_text or "").lower()

    if re.search(r"\b(senior|lead|staff|principal)\b", t):
        return "SENIOR"
    if re.search(r"\b(3\+|4\+|5\+)\s*years\b", t):
        return "MID"
    if re.search(r"\b(1\+|2\+)\s*years\b", t):
        return "ENTRY_OR_MID"

    return "ENTRY"


def _lane_from_role_family(role_family: str) -> str:
    rf = (role_family or "").strip().lower()
    rf_norm = re.sub(r"[\W_]+", " ", rf).strip()

    fullstack_terms = [
        "full stack", "fullstack", "mern", "mean",
        "web developer", "software engineer web", "application developer"
    ]
    if any(t in rf_norm for t in fullstack_terms):
        return "FULLSTACK"

    fe_terms = ["frontend", "front end", "ui developer", "react developer", "next js developer", "angular developer"]
    if any(t in rf_norm for t in fe_terms):
        return "FRONTEND"

    be_terms = ["backend", "back end", "api developer", "server side", "node developer", "java developer", "dotnet developer"]
    if any(t in rf_norm for t in be_terms):
        return "BACKEND"

    data_terms = ["data engineer", "ml engineer", "machine learning", "data scientist"]
    if any(t in rf_norm for t in data_terms):
        return "DATA"

    return "GENERAL"


def _dedupe_phrases(text: str) -> str:
    s = re.sub(r"\s+", " ", (text or "").strip())
    parts = [p.strip() for p in re.split(r"(?<=[.!?])\s+", s) if p.strip()]
    out = []
    seen = set()
    for p in parts:
        key = re.sub(r"[^a-z0-9]+", " ", p.lower()).strip()
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return " ".join(out).strip()


def _clamp_words(text: str, max_words: int = 60) -> str:
    words = (text or "").split()
    if len(words) <= max_words:
        return (text or "").strip()
    return " ".join(words[:max_words]).rstrip(" ,;:.") + "."


def _rewrite_summary(master: dict, role_family: str, jd_terms: List[str], jd_text: str) -> str:
    base_raw = str(master.get("summary") or master.get("objective") or "").strip()
    archetype = master.get("_jd_archetype", "GENERAL")

    lane = _lane_from_role_family(role_family)
    level = _detect_level(jd_text)

    learned = top_terms(role_family=role_family, limit=12)
    learned = [x for x in learned if x and x.lower() not in _NOISE]

    jd_set = {str(x).lower() for x in (jd_terms or [])}

    def score_term(t: str) -> float:
        tl = str(t).lower().strip()
        if not tl or tl in _NOISE:
            return 0.0
        hit = 2.0 if tl in jd_set else 0.0
        return hit + float(term_weight(t, role_family) or 0.0)

    candidates = _dedup_keep((jd_terms or [])[:40] + learned[:20])
    ranked = sorted(candidates, key=score_term, reverse=True)

    filtered_terms = filter_tech_terms(ranked)[:6]
    if len(filtered_terms) >= 2:
        tech_blob = ", ".join(filtered_terms[:-1]) + " and " + filtered_terms[-1]
    else:
        tech_blob = ", ".join(filtered_terms)

    tech_blob = tech_blob.strip()

    if lane == "FRONTEND":
        lead = "Frontend engineer building polished, accessible, high-performance web UIs." if level in ("MID", "SENIOR") \
               else "Frontend engineer focused on modern UI development with strong fundamentals."
        focus = "Design consistency, accessibility, usability, and performance hygiene."
    elif lane == "BACKEND":
        lead = "Backend engineer delivering reliable APIs and production-minded services." if level in ("MID", "SENIOR") \
               else "Backend-focused engineer with strong fundamentals in APIs and databases."
        focus = "Clean interfaces, debugging, and maintainable delivery."
    elif lane == "FULLSTACK":
        if archetype == "BACKEND_WEB":
            lead = "Junior full-stack engineer focused on backend services, REST APIs, and relational database integration."
            focus = "Clean modular backend code, API integration, SQL data modeling, and collaborative full-stack delivery."
        else:
            lead = "Full-stack engineer delivering polished UIs and reliable APIs with production-minded execution." if level in ("MID", "SENIOR") \
                else "Full-stack engineer with strong fundamentals across frontend, backend and databases."
            focus = "End-to-end ownership with performance hygiene, API quality and maintainable delivery."
    elif lane == "DATA":
        lead = "Data-focused engineer delivering clean pipelines, analysis, and dashboards." if level in ("MID", "SENIOR") \
               else "Data-focused engineer with strong fundamentals in analysis and pipelines."
        focus = "Repeatable runs, correctness checks, and clear communication."
    else:
        lead = "Software engineer delivering maintainable features with strong execution." if level in ("MID", "SENIOR") \
               else "Early-career software engineer with strong fundamentals and project delivery."
        focus = "Structured debugging, clean code, and documentation."

    s = base_raw.strip() if len(base_raw.split()) >= 16 else lead

    if tech_blob:
        s = f"{s} Core strengths: {tech_blob}."

    alignment = master.get("_alignment") or {}
    coverage = alignment.get("coverage_percent", 100)
    missing = alignment.get("high_priority_missing", [])

    if coverage < 70 and missing:
        related = [
            m for m in missing
            if any(m in str(v).lower() for v in master.get("skills", {}).get("Core", []))
        ]
        if related:
            emphasis = ", ".join(related[:2])
            s = f"{s} Actively expanding expertise in {emphasis}."

    s = f"{s} {focus} {_SAFE_ENGINEERING_PHRASES[0]}"
    s = _dedupe_phrases(s)
    s = _clamp_words(s, 60)
    return _norm(s)


# ============================================================
# Project intelligence
# ============================================================
def _token_set(text: str) -> set[str]:
    return set(_norm_low(t) for t in _TOKEN_RE.findall(text or ""))


def _reorder_tech_stack(tech: str, jd_terms: List[str], role_family: str) -> str:
    parts = re.split(r"[,/|]+", tech or "")
    items = [_norm(p) for p in parts if _norm(p)]
    if not items:
        return _norm(tech or "")

    jd_set = {x.lower() for x in jd_terms}

    def score(x: str) -> float:
        xl = x.lower()
        hit = 3.0 if xl in jd_set else 0.0
        return hit + term_weight(x, role_family)

    items = _dedup_keep(items)
    items_sorted = sorted(items, key=score, reverse=True)
    return ", ".join(items_sorted[:10])


def _safe_inject_keywords(bullet: str, jd_terms: List[str], proj_text: str, role_family: str, *, debug: bool = False) -> str:
    b = _norm(bullet)
    if not b:
        return b

    proj_tokens = _token_set(proj_text)
    cand = []
    for t in jd_terms:
        tl = t.lower()
        if tl in _NOISE:
            continue
        if tl in proj_tokens:
            cand.append(t)
            continue
        for p in proj_tokens:
            if p and (p in tl or tl in p) and len(p) >= 4:
                cand.append(t)
                break

    cand = _dedup_keep(cand)
    cand.sort(key=lambda x: term_weight(x, role_family), reverse=True)
    cand = cand[:2]

    if not cand:
        return b

    if debug:
        tag = "; ".join(cand)
        if tag and tag.lower() not in b.lower():
            return f"{b} (Aligned: {tag})"

    return b


def _tailor_project_bullets(proj: dict, jd_terms: List[str], role_family: str, max_bullets: int = 4) -> dict:
    proj2 = dict(proj)
    bullets = proj.get("bullets", []) or []
    if not isinstance(bullets, list):
        bullets = [str(bullets)]

    name = _norm(str(proj.get("name", "")))
    tech = _norm(str(proj.get("tech", "")))
    org = _norm(str(proj.get("org", "")))
    proj_text = " ".join([name, tech, org] + [str(x) for x in bullets])

    jd_set = {x.lower() for x in jd_terms}

    scored: List[Tuple[float, str]] = []
    for b in bullets:
        s = _strengthen_verbs(str(b))
        toks = _token_set(s)
        hit = sum(1 for t in toks if t in jd_set)
        learned_bonus = sum(0.05 * term_weight(t, role_family) for t in toks)
        scored.append((float(hit) + float(learned_bonus), s))

    scored_sorted = sorted(scored, key=lambda x: x[0], reverse=True)
    new_bullets = [b for _, b in scored_sorted if _norm(b)]
    new_bullets = new_bullets[:max_bullets]

    new_bullets = [_safe_inject_keywords(b, jd_terms, proj_text, role_family, debug=False) for b in new_bullets]

    if len(new_bullets) < 3:
        new_bullets.append(_SAFE_ENGINEERING_PHRASES[2])

    proj2["bullets"] = _dedup_keep(new_bullets)

    if "tech" in proj2 and isinstance(proj2.get("tech"), str):
        proj2["tech"] = _reorder_tech_stack(proj2.get("tech") or "", jd_terms, role_family)

    return proj2


def _score_project(proj: dict, jd_terms: List[str], role_family: str, alignment: Optional[dict] = None) -> float:
    jd_set = {x.lower() for x in jd_terms}
    name = _norm(str(proj.get("name", "")))
    org = _norm(str(proj.get("org", "")))
    tech = _norm(str(proj.get("tech", "")))
    bullets = proj.get("bullets", []) or []

    text = " ".join([name, org, tech] + ([str(b) for b in bullets] if isinstance(bullets, list) else [str(bullets)]))
    tokens = _token_set(text)

    hits = sum(1 for t in tokens if t in jd_set)
    learned = sum(0.02 * term_weight(t, role_family) for t in tokens)
    base = 1.0 if isinstance(bullets, list) and len(bullets) >= 3 else 0.0

    boost = 0.0
    if alignment:
        missing = alignment.get("high_priority_missing", [])
        for m in missing:
            for tok in tokens:
                if tok and (tok in m or m in tok):
                    boost += 0.5

    archetype = alignment.get("archetype") if alignment else None
    penalty = 0.0
    if archetype == "BACKEND_WEB":
        name_text = name.lower()
        if "machine" in name_text or "model" in name_text or "ml" in name_text:
            penalty = 0.5

    return float(hits) + float(learned) + base + boost - penalty


def _select_projects(master: dict, jd_terms: List[str], role_family: str, k: int = 2) -> Tuple[List[dict], List[dict]]:
    projects = master.get("projects", []) or []
    if not isinstance(projects, list):
        return [], []

    scored: List[Tuple[float, dict]] = []
    for p in projects:
        if isinstance(p, dict):
            alignment = master.get("_alignment")
            scored.append((_score_project(p, jd_terms, role_family, alignment), p))

    scored.sort(key=lambda x: x[0], reverse=True)
    selected = [copy.deepcopy(p) for _, p in scored[:k]]
    leftover = [copy.deepcopy(p) for _, p in scored[k:]]

    selected = [_tailor_project_bullets(p, jd_terms, role_family) for p in selected]
    return selected, leftover


# ============================================================
# Weighted skill grouping
# ============================================================
def _reorder_skills(master: dict, jd_terms: List[str], role_family: str) -> dict:
    skills = master.get("skills", {}) or {}
    if not isinstance(skills, dict):
        return master

    jd_set = {x.lower() for x in jd_terms}
    alignment = master.get("_alignment") or {}
    missing = alignment.get("high_priority_missing", [])

    def item_score(s: str) -> float:
        sl = _norm_low(s)
        hit = 3.0 if sl in jd_set else 0.0
        learned = 0.15 * term_weight(s, role_family)

        proximity = 0.0
        for m in missing:
            if sl and (sl in m or m in sl):
                proximity += 0.5

        return hit + learned + proximity

    new_items_by_cat: Dict[str, List[str]] = {}
    cat_scores: List[Tuple[float, str]] = []

    for cat, items in skills.items():
        cat_name = str(cat).strip() or "Skills"
        if isinstance(items, list):
            clean = _dedup_keep([str(x) for x in items if str(x).strip()])
            ranked = sorted(clean, key=lambda x: item_score(x), reverse=True)
            new_items_by_cat[cat_name] = ranked
            cs = sum(item_score(x) for x in ranked[:6])
            cat_scores.append((cs, cat_name))
        else:
            s = str(items).strip()
            new_items_by_cat[cat_name] = [s] if s else []
            cat_scores.append((item_score(s) if s else 0.0, cat_name))

    cat_scores.sort(key=lambda x: x[0], reverse=True)
    ordered_cats = [c for _, c in cat_scores if c]

    skills2: Dict[str, Any] = {}
    for c in ordered_cats:
        arr = new_items_by_cat.get(c, [])
        if arr:
            skills2[c] = arr

    master2 = dict(master)
    master2["skills"] = skills2
    return master2


# ============================================================
# Resume–JD Alignment Scoring
# ============================================================
def _collect_resume_text(master: dict, *, include_summary: bool = False) -> str:
    parts: List[str] = []

    if include_summary:
        parts.append(str(master.get("summary", "")))

    for _, items in (master.get("skills", {}) or {}).items():
        if isinstance(items, list):
            parts.extend([str(x) for x in items])
        else:
            parts.append(str(items))

    for p in (master.get("projects") or []):
        if isinstance(p, dict):
            parts.append(str(p.get("name", "")))
            parts.append(str(p.get("tech", "")))
            parts.extend([str(b) for b in (p.get("bullets") or [])])

    for e in (master.get("experience") or []):
        if isinstance(e, dict):
            parts.append(str(e.get("title", "")))
            parts.append(str(e.get("org", "")))
            parts.extend([str(b) for b in (e.get("bullets") or [])])

    return _norm_low(" ".join(parts))


def _alignment_score(master: dict, jd_terms: List[str], role_family: str) -> dict:
    resume_text = _collect_resume_text(master, include_summary=False)

    jd_clean = filter_tech_terms(jd_terms)
    jd_set = {t.lower() for t in jd_clean}

    matched = []
    missing = []

    for term in jd_set:
        if term in resume_text:
            matched.append(term)
        else:
            missing.append(term)

    coverage = 0.0
    if jd_set:
        coverage = round((len(matched) / len(jd_set)) * 100, 2)

    category_scores = {}
    skills = master.get("skills", {}) or {}
    if isinstance(skills, dict):
        for cat, items in skills.items():
            if not isinstance(items, list):
                continue
            score = sum(1 for x in items if str(x).lower() in jd_set)
            if score > 0:
                category_scores[cat] = score

    strongest_category = None
    if category_scores:
        strongest_category = max(category_scores, key=category_scores.get)

    return {
        "coverage_percent": coverage,
        "matched_terms": sorted(matched),
        "missing_terms": sorted(missing)[:10],
        "high_priority_missing": sorted(missing)[:5],
        "strongest_skill_category": strongest_category,
        "archetype": master.get("_jd_archetype"),
    }


# ============================================================
# Archetype detection (FIXED to satisfy FULLSTACK test)
# ============================================================
def _detect_jd_archetype(jd_terms: List[str], role_family: str = "") -> str:
    """
    Deterministic archetype detection.
    FULLSTACK_WEB if strong frontend + backend signals are both present.
    """

      # ✅ Hard override: if the caller explicitly selected Full Stack, respect it.
    rf = (role_family or "").lower()
    rf_norm = re.sub(r"[\W_]+", " ", rf).strip()
    if "full stack" in rf_norm or "fullstack" in rf_norm:
        return "FULLSTACK_WEB"

    if not jd_terms:
        return "GENERAL"

    aliases = {
        "reactjs": "react",
        "react.js": "react",
        "nodejs": "node.js",
        "node": "node.js",
        "html5": "html",
        "css3": "css",
        "wcag 2.1": "wcag",
        "styled components": "styled-components",
        "redux toolkit": "redux toolkit",
        "postgres": "postgresql",
    }

    terms: List[str] = []
    for t in (jd_terms or []):
        s = _norm_low(str(t))
        if not s:
            continue
        s = aliases.get(s, s)
        terms.append(s)

    term_set = set(terms)

    backend = {
        "python", "java", "sql", "postgresql", "mysql", "mongodb", "redis",
        "rest", "graphql", "backend", "microservices",
        "spring", "spring boot", "express", "node.js", ".net", "asp.net", "api"
    }
    frontend = {
        "react", "next.js", "angular", "vue",
        "javascript", "typescript", "html", "css",
        "tailwindcss", "styled-components", "storybook",
        "redux", "redux toolkit", "zustand", "mobx",
        "wcag", "accessibility", "lighthouse",
        "webpack", "vite", "rollup",
        "figma", "adobe xd"
    }
    data_ml = {"machine learning", "ml", "model", "tensorflow", "pytorch", "pandas", "numpy", "scikit-learn"}
    infra = {"aws", "azure", "gcp", "docker", "kubernetes", "devops", "terraform", "linux"}

    # learned weight helper
    def w(t: str) -> float:
        try:
            return float(term_weight(t, role_family) or 0.0)
        except Exception:
            return 0.0

    GENERIC = {"rest", "api", "graphql"}

    def score(bucket: set[str]) -> float:
        s = 0.0
        for t in term_set:
            if t in bucket:
                base = 0.4 if t in GENERIC else 1.0
                s += base + 0.05 * w(t)
        return s

    def hits(bucket: set[str]) -> int:
        return sum(1 for t in term_set if t in bucket)

    scores = {
        "BACKEND_WEB": score(backend),
        "FRONTEND_WEB": score(frontend),
        "DATA_ML": score(data_ml),
        "INFRA": score(infra),
    }

    fe_hits = hits(frontend)
    be_hits = hits(backend)

    # FULLSTACK rule: both sides strong, neither dominates too hard
    if fe_hits >= 3 and be_hits >= 3:
        # If backend isn't 2x stronger than frontend (or vice versa), call it fullstack
        if max(fe_hits, be_hits) <= 2 * min(fe_hits, be_hits):
            return "FULLSTACK_WEB"

    # fallback: best score
    best = max(scores, key=scores.get)
    if scores[best] <= 0:
        return "GENERAL"

    # If both are meaningfully present by score, treat as fullstack
    fe, be = scores["FRONTEND_WEB"], scores["BACKEND_WEB"]
    if fe > 0.0 and be > 0.0:
        ratio = min(fe, be) / max(fe, be)
        if ratio >= 0.45:
            return "FULLSTACK_WEB"

    return best


# ============================================================
# Output defaults (FIXES missing "projects" key)
# ============================================================
def _ensure_defaults(m: dict) -> dict:
    if not isinstance(m, dict):
        m = {}

    if m.get("summary") is None:
        m["summary"] = ""
    m.setdefault("summary", "")

    if m.get("skills") is None:
        m["skills"] = {}
    m.setdefault("skills", {})

    if m.get("projects") is None:
        m["projects"] = []
    m.setdefault("projects", [])

    if m.get("experience") is None:
        m["experience"] = []
    m.setdefault("experience", [])

    return m


def apply_intelligence(
    master: dict,
    role_family: str = "",
    jd_text: str = "",
    jd_struct: Optional[dict] = None,
    *,
    summary_mode: Optional[str] = None,
) -> dict:
    """
    summary_mode:
      - "assist": only generate if summary is empty
      - "auto": always generate/overwrite
      - "off": never touch summary
    """
    master0 = master or {}
    master2 = copy.deepcopy(master0)
    master2 = _ensure_defaults(master2)

    role_family = (role_family or "").strip()
    jd_text = (jd_text or "").strip()

    jd_terms = _extract_jd_terms(jd_text, jd_struct if isinstance(jd_struct, dict) else None)
    master2["_jd_archetype"] = _detect_jd_archetype(jd_terms, role_family=role_family)

    settings = _load_settings()
    mode = _summary_mode(settings)

    if summary_mode is None:
        if mode == "always_custom":
            summary_mode = "off"
        elif mode == "always_dynamic":
            summary_mode = "auto"
        else:
            summary_mode = "assist"

    existing_summary = str(master2.get("summary") or "").strip()

    if summary_mode == "off":
        pass
    elif summary_mode == "assist":
        if not existing_summary:
            master2["summary"] = _rewrite_summary(master2, role_family, jd_terms, jd_text)
    elif summary_mode == "auto":
        master2["summary"] = _rewrite_summary(master2, role_family, jd_terms, jd_text)
    else:
        if not existing_summary:
            master2["summary"] = _rewrite_summary(master2, role_family, jd_terms, jd_text)

    master2 = _reorder_skills(master2, jd_terms, role_family)

    selected, leftover = _select_projects(master2, jd_terms, role_family, k=2)
    # ALWAYS keep "projects" key present (default empty is fine)
    if selected:
        master2["projects"] = selected
        master2["_intel_leftover_projects"] = leftover
    else:
        master2.setdefault("projects", [])

    exp = master2.get("experience", []) or []
    if isinstance(exp, list):
        new_exp = []
        for e in exp:
            if not isinstance(e, dict):
                new_exp.append(e)
                continue
            e2 = dict(e)
            bullets = e2.get("bullets", []) or []
            if isinstance(bullets, list):
                e2["bullets"] = [_strengthen_verbs(str(b)) for b in bullets if _norm(str(b))]
            new_exp.append(e2)
        master2["experience"] = new_exp
    else:
        master2["experience"] = []

    master2["_intel_jd_terms"] = jd_terms[:30]
    master2["_alignment"] = _alignment_score(master2, jd_terms, role_family)
    master2["_scorecard"] = _scorecard(master2)

    master2 = _ensure_defaults(master2)
    return master2


# ============================================================
# Quality enforcement (safe)
# ============================================================
def _word_count_from_blocks(blocks: dict) -> int:
    parts: List[str] = []
    parts.append(str(blocks.get("summary", "")))

    for x in (blocks.get("skills_lines") or []):
        parts.append(str(x))

    for e in (blocks.get("experience") or []):
        if isinstance(e, dict):
            parts.append(str(e.get("title", "")))
            parts.append(str(e.get("org", e.get("company", ""))))
            parts.extend([str(b) for b in (e.get("bullets") or [])])

    for p in (blocks.get("projects") or []):
        if isinstance(p, dict):
            parts.append(str(p.get("name", "")))
            parts.append(str(p.get("tech", "")))
            parts.extend([str(b) for b in (p.get("bullets") or [])])

    for ed in (blocks.get("education") or []):
        if isinstance(ed, dict):
            parts.append(str(ed.get("degree", "")))
            parts.append(str(ed.get("school", "")))

    for c in (blocks.get("certifications") or []):
        parts.append(str(c))
    for pub in (blocks.get("publications") or []):
        parts.append(str(pub))

    text = " ".join([p for p in parts if p and str(p).strip()])
    return len(re.findall(r"\b\w+\b", text))


def enforce_quality(blocks: dict, min_words: int = DEFAULT_MIN_WORDS) -> dict:
    wc = _word_count_from_blocks(blocks)
    if wc >= min_words:
        blocks["summary"] = _clamp_words(_dedupe_phrases(str(blocks.get("summary", ""))), 60)
        return blocks

    s = str(blocks.get("summary", "")).strip()
    add = " Additional strengths: debugging, version control, basic testing, and clean documentation in iterative delivery."
    if add.lower() not in s.lower():
        blocks["summary"] = (s + add).strip()

    blocks["summary"] = _clamp_words(_dedupe_phrases(str(blocks.get("summary", ""))), 60)
    return blocks


def _scorecard(master: dict) -> dict:
    summary = str(master.get("summary") or "")
    skills = master.get("skills") or {}
    projects = master.get("projects") or []
    alignment = master.get("_alignment") or {}
    archetype = master.get("_jd_archetype") or "GENERAL"

    comma_count = summary.count(",")
    leak = ("aligned:" in summary.lower())

    skill_items = 0
    if isinstance(skills, dict):
        for _, items in skills.items():
            if isinstance(items, list):
                skill_items += len(items)
            elif str(items).strip():
                skill_items += 1

    proj_count = len([p for p in projects if isinstance(p, dict)])
    proj_bullets = 0
    for p in projects:
        if isinstance(p, dict):
            proj_bullets += len(p.get("bullets") or [])

    coverage = float(alignment.get("coverage_percent", 0.0) or 0.0)
    missing = alignment.get("missing_terms") or []
    missing_count = len(missing) if isinstance(missing, list) else 0

    return {
        "archetype": archetype,
        "alignment_coverage": coverage,
        "missing_count": missing_count,
        "summary_commas": comma_count,
        "skills_count": skill_items,
        "projects_count": proj_count,
        "project_bullets_count": proj_bullets,
        "leak_detected": bool(leak),
    }