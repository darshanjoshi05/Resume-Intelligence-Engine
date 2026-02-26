# jd_extract.py (v2.5) — Offline JD Intelligence (TECH-ONLY + COMPAT KEYS)
# Adds compatibility keys:
#   must_have_skills, tools_tech, nice_to_have_skills
# Also adds:
#   role_level: INTERN | ENTRY | MID | SENIOR
#
# Output keys (stable):
#   company, role_title, job_location, work_mode, relocation_required, role_level
#   hard_skills, role_signals, jd_signals, keywords
#   must_have_skills, tools_tech, nice_to_have_skills
#   signal {size, note}

from __future__ import annotations
import re
from typing import Tuple, List, Dict


# -----------------------------
# Canonicalization (normalize variants)
# -----------------------------
_CANON = {
    # frontend
    "react.js": "react",
    "reactjs": "react",
    "next.js": "nextjs",
    "nextjs": "nextjs",
    "angular.js": "angular",
    "vue.js": "vue",
    "node.js": "node",
    "nodejs": "node",

    # db
    "postgres": "postgresql",
    "postgre": "postgresql",
    "postgre sql": "postgresql",
    "postgre-sql": "postgresql",
    "sqlserver": "sql server",
    "mssql": "sql server",
    "ms sql": "sql server",

    # api/devops
    "restful": "rest",
    "apis": "api",
    "ci/cd": "cicd",
    "ci-cd": "cicd",
    "k8s": "kubernetes",

    # microsoft
    "dotnet": ".net",
    ".net": ".net",
    "asp.net": "asp.net",
    "aspnet": "asp.net",

    # lang shortcuts
    "js": "javascript",
    "ts": "typescript",

    # ml shortcuts
    "ml": "machine learning",
    "ai/ml": "machine learning",

    # state mgmt
    "redux toolkit": "redux",
}

def _norm(s: str) -> str:
    t = (s or "").strip().lower()
    t = t.replace("•", " ").replace("·", " ").replace("—", "-").replace("–", "-")
    t = re.sub(r"\s+", " ", t).strip()
    return _CANON.get(t, t)

def _dedup_keep_order(items: List[str]) -> List[str]:
    out, seen = [], set()
    for x in items:
        k = _norm(x)
        if not k:
            continue
        if k in seen:
            continue
        seen.add(k)
        out.append(k)
    return out


# -----------------------------
# Noise control
# -----------------------------
HR_NOISE_SUBSTRINGS = [
    "equal opportunity", "eeo", "veteran", "disabled", "disability",
    "accommodation", "reasonable accommodation",
    "background check", "drug test",
    "work authorization", "e-verify", "immigration", "sponsorship", "right to work",
    "privacy", "cookie", "terms of use", "notice to prospective employees",
    "benefit", "benefits", "insurance", "medical", "dental", "vision", "hsa", "fsa",
    "401k", "pto", "paid time off", "holidays", "leave",
    "compensation", "salary", "bonus", "bonuses", "relocation benefits",
    "employee assistance", "wellness", "life insurance",
    "regular attendance", "attendance", "reliable attendance",
    "drug free", "harassment", "policy", "policies",
    "hospital", "accident", "injury", "incident", "commuter", "transportation",
]

SOFT_FLUFF_PHRASES = [
    "problem solver", "team player", "fast learner", "self starter",
    "excellent communication", "strong communication",
    "diverse set of backgrounds", "who you are", "what you will do",
    "about the role", "about us", "we are looking for",
]

STOPWORDS = {
    "a","an","the","and","or","to","of","in","on","for","with","as","at","by","from",
    "we","you","our","your","their","they","them","this","that","these","those",
    "will","can","may","must","should","able","ability","including","include","etc",
    "years","year","experience","preferred","required","minimum","qualifications",
    "responsibilities","requirements","role","position","job",
}

def _is_url_or_domain(t: str) -> bool:
    tt = t.lower()
    if "http://" in tt or "https://" in tt or "www." in tt:
        return True
    return bool(re.search(r"\b[a-z0-9\-]+\.(com|org|net|io|ai|edu)\b", tt))

def _looks_like_sentence_fragment(t: str) -> bool:
    words = re.findall(r"[a-zA-Z]+", t.lower())
    if len(words) >= 6:
        stop = sum(1 for w in words if w in STOPWORDS)
        if stop / max(1, len(words)) > 0.55:
            return True
    return False

def _has_tech_shape(t: str) -> bool:
    low = t.lower()
    if re.search(r"[+#./]", t):
        return True
    if re.search(r"\b(c\+\+|c#|\.net|asp\.net|node\.js)\b", low):
        return True
    if re.search(r"\b(aws|gcp|azure|sql|nosql|etl|api|rest|graphql|react|nextjs|python|java|docker|kubernetes)\b", low):
        return True
    return False

def _is_noise_item(raw: str) -> bool:
    t = (raw or "").strip()
    if not t:
        return True
    if _is_url_or_domain(t):
        return True
    low = t.lower()
    if len(low) <= 1:
        return True
    if len(low) > 140:
        return True

    for bad in HR_NOISE_SUBSTRINGS:
        if bad in low:
            return True
    for fluff in SOFT_FLUFF_PHRASES:
        if fluff in low:
            return True

    if _looks_like_sentence_fragment(low) and not _has_tech_shape(low):
        return True

    return False

def _clean_item(raw: str) -> str:
    t = (raw or "").strip()
    t = re.sub(r"^[\-\*\u2022]+", "", t).strip()
    t = re.sub(r"\s+", " ", t).strip(" ;:,.")
    t = t.replace("\\", "/")
    return _norm(t)


# -----------------------------
# Work mode / relocation / role level
# -----------------------------
def detect_work_mode(jd: str) -> str:
    t = jd.lower()
    if re.search(r"\bhybrid\b", t):
        return "HYBRID"
    if re.search(r"\bremote\b|\bwork from home\b|\bwfh\b", t):
        return "REMOTE"
    if re.search(r"\bon[-\s]?site\b|\bonsite\b", t):
        return "ONSITE"
    return "UNKNOWN"

def detect_relocation_required(jd: str) -> bool:
    t = jd.lower()
    if re.search(r"\brelocation (is )?required\b", t):
        return True
    if re.search(r"\bmust be willing to relocate\b", t):
        return True
    if re.search(r"\bno relocation\b|\brelocation not (provided|available)\b", t):
        return False
    return False

def infer_role_level(jd: str, role_title: str = "") -> str:
    """
    Very simple + safe:
    INTERN | ENTRY | MID | SENIOR
    """
    t = (jd or "").lower()
    rt = (role_title or "").lower()

    if re.search(r"\bintern\b|\binternship\b", t) or "intern" in rt:
        return "INTERN"

    # explicit senior cues
    if re.search(r"\bsenior\b|\bstaff\b|\bprincipal\b|\blead\b|\barchitect\b", t) or any(x in rt for x in ["senior", "lead", "staff", "principal", "architect"]):
        return "SENIOR"

    # years-based
    m = re.findall(r"(\d+)\s*\+?\s*(?:years|yrs)\b", t)
    years = 0
    for x in m:
        try:
            years = max(years, int(x))
        except Exception:
            pass

    if years >= 5:
        return "SENIOR"
    if years >= 2:
        return "MID"

    # entry cues
    if re.search(r"\bentry\b|\bgraduate\b|\bnew grad\b|\bjunior\b", t) or any(x in rt for x in ["junior", "entry"]):
        return "ENTRY"

    return "ENTRY"


# -----------------------------
# Company / Role / Location
# -----------------------------
def _normalize_lines(jd: str) -> List[str]:
    text = jd.replace("\t", " ")
    lines = [re.sub(r"\s+", " ", l).strip() for l in text.splitlines()]
    return [l for l in lines if l]

def extract_company_role(jd: str) -> Tuple[str, str]:
    lines = _normalize_lines(jd)
    first_block = "\n".join(lines[:80])

    role = ""
    company = ""

    m = re.search(r"(?:job title|position|role)\s*[:\-]\s*(.{3,120})", first_block, re.I)
    if m:
        role = m.group(1).strip()

    m = re.search(r"(?:company|employer|organization)\s*[:\-]\s*(.{2,120})", first_block, re.I)
    if m:
        company = m.group(1).strip()

    if lines and not role:
        m = re.match(r"^([A-Za-z0-9&.,\-/ ]{2,60})\s*[-|–]\s*([A-Za-z0-9&.,\-/ ]{3,80})$", lines[0])
        if m:
            company = company or m.group(1).strip()
            role = role or m.group(2).strip()

    if not role:
        for l in lines[:25]:
            low = l.lower()
            if 4 <= len(l) <= 80 and not low.startswith(("location", "about", "responsibilities", "requirements", "overview")):
                if sum(ch.isalpha() for ch in l) >= 6:
                    role = l
                    break

    if not company:
        m = re.search(r"\babout\s+([A-Z][A-Za-z0-9&.\- ]{2,60})\b", first_block)
        if m:
            company = m.group(1).strip()

    return company.strip(), role.strip()

_US_CITY_STATE = re.compile(r"\b([A-Z][a-zA-Z]+(?:\s[A-Z][a-zA-Z]+)*)\,\s([A-Z]{2})\b")
_ZIP = re.compile(r"\b\d{5}(?:-\d{4})?\b")

def extract_location(jd: str) -> str:
    lines = _normalize_lines(jd)
    first_block = "\n".join(lines[:120])

    m = re.search(r"(?:location)\s*[:\-]\s*(.{2,120})", first_block, re.I)
    if m:
        loc = m.group(1).strip().split("|")[0].strip()
        return re.sub(r"\s+", " ", loc)

    m = _US_CITY_STATE.search(first_block)
    if m:
        return f"{m.group(1)}, {m.group(2)}"

    m = re.search(r"\(([^)]+)\)", first_block)
    if m:
        inside = m.group(1).strip()
        if _US_CITY_STATE.search(inside):
            mm = _US_CITY_STATE.search(inside)
            return f"{mm.group(1)}, {mm.group(2)}"
        if re.search(r"\bremote\b|\bhybrid\b|\bon[-\s]?site\b", inside, re.I):
            return inside

    if _ZIP.search(first_block):
        for l in lines[:160]:
            if _ZIP.search(l):
                return l

    return ""


# -----------------------------
# Section parsing
# -----------------------------
_SECTION_HEADINGS = {
    "must": [
        r"\brequirements\b",
        r"\brequired qualifications\b",
        r"\bminimum qualifications\b",
        r"\bmust have\b",
        r"\bwhat you bring\b",
        r"\bqualifications\b",
    ],
    "nice": [
        r"\bpreferred qualifications\b",
        r"\bpreferred\b",
        r"\bnice to have\b",
        r"\bbonus\b",
        r"\bplus\b",
    ],
    "tools": [
        r"\btools\b",
        r"\btechnology\b",
        r"\btech stack\b",
        r"\bstack\b",
        r"\bskills\b",
        r"\bwhat you'll use\b",
        r"\bwhat you will use\b",
    ],
    "resp": [
        r"\bresponsibilities\b",
        r"\bwhat you will do\b",
        r"\bwhat you'll do\b",
        r"\bduties\b",
    ],
}

def _split_sections(jd: str) -> Dict[str, str]:
    lines = jd.splitlines()
    hits: List[Tuple[int, str]] = []

    for i, raw in enumerate(lines):
        l = (raw or "").strip()
        if not l:
            continue
        low = l.lower()
        for key, pats in _SECTION_HEADINGS.items():
            for pat in pats:
                if re.search(pat, low):
                    hits.append((i, key))
                    break

    if not hits:
        return {"must": "", "nice": "", "tools": "", "resp": "", "other": jd}

    hits = sorted(hits, key=lambda x: x[0])
    out = {"must": "", "nice": "", "tools": "", "resp": "", "other": ""}

    for idx, (start_i, key) in enumerate(hits):
        end_i = hits[idx + 1][0] if idx + 1 < len(hits) else len(lines)
        block = "\n".join(lines[start_i:end_i]).strip()
        out[key] = (out[key] + "\n" + block).strip()

    return out


# -----------------------------
# TECH vocab (hard skills + role signals)
# -----------------------------
HARD_SKILLS = [
    "python", "java", "javascript", "typescript", "c", "c++", "c#", "go", "ruby", "sql",
    "react", "nextjs", "angular", "vue", "html", "css", "tailwindcss", "styled components",
    "node", "express", ".net", "asp.net", "spring", "spring boot",
    "postgresql", "mysql", "sql server", "mongodb", "redis", "oracle", "nosql",
    "aws", "azure", "gcp", "docker", "kubernetes",
    "git", "github", "bitbucket", "webpack", "vite", "rollup",
    "jest", "cypress", "playwright",
    "pandas", "numpy", "scikit-learn",
    "power bi", "tableau",
    "kafka",
    "redux", "zustand", "mobx",
]

HARD_SKILLS_SET = set(_norm(x) for x in HARD_SKILLS)

ROLE_SIGNALS = [
    "api", "rest", "graphql",
    "microservices", "distributed systems",
    "data structures", "algorithms", "oop", "object oriented programming",
    "system design", "design patterns",
    "unit testing", "integration testing", "test automation",
    "performance optimization", "debugging",
    "accessibility", "wcag",
    "state management",
    "code splitting", "lazy loading", "lighthouse",
    "security", "authentication", "authorization",
    "logging", "monitoring",
    "etl", "data pipelines",
]

ROLE_SIGNALS_SET = set(_norm(x) for x in ROLE_SIGNALS)
TECH_TOKEN = re.compile(r"\b[a-zA-Z][a-zA-Z0-9\.\+\-#/]{1,}\b")


# -----------------------------
# Extraction helpers
# -----------------------------
def _extract_candidate_lines(block: str) -> List[str]:
    if not block:
        return []
    lines = [re.sub(r"\s+", " ", l).strip() for l in block.splitlines() if l.strip()]
    out: List[str] = []
    for l in lines:
        low = l.lower()

        if re.match(r"^(requirements|preferred|required|minimum|nice to have|tools|technology|tech stack|skills|responsibilities|duties)\b", low):
            continue

        if l.startswith(("-", "•", "*")):
            l = l.lstrip("-•*").strip()

        if "," in l and len(l) <= 140:
            parts = [p.strip() for p in l.split(",") if p.strip()]
            if len(parts) >= 2:
                out.extend(parts)
                continue

        out.append(l)
    return out

def _keep_only_tech(items: List[str]) -> List[str]:
    cleaned: List[str] = []
    for it in items:
        it2 = _clean_item(it)
        if _is_noise_item(it2):
            continue

        n = _norm(it2)

        if n in HARD_SKILLS_SET or n in ROLE_SIGNALS_SET:
            cleaned.append(n)
            continue

        if _has_tech_shape(it2):
            if n.isalpha() and len(n) >= 3 and n not in HARD_SKILLS_SET and n not in ROLE_SIGNALS_SET:
                if n in {"api", "oop", "etl", "sql", "aws", "gcp", "cicd", "wcag"}:
                    cleaned.append(n)
                continue
            cleaned.append(n)
            continue

    return _dedup_keep_order(cleaned)

def extract_keywords_tech_only(jd: str) -> List[str]:
    t = jd.lower()
    found: List[str] = []

    phrases = sorted(list(HARD_SKILLS_SET | ROLE_SIGNALS_SET), key=len, reverse=True)
    for ph in phrases:
        if ph and ph in t:
            found.append(ph)

    tokens = TECH_TOKEN.findall(jd)
    for tok in tokens:
        low = tok.lower()
        if len(low) < 2:
            continue
        if low.isalpha() and low in STOPWORDS:
            continue

        n = _norm(low)

        if n in HARD_SKILLS_SET or n in ROLE_SIGNALS_SET:
            found.append(n)
            continue

        if _has_tech_shape(tok):
            if n.isalpha() and n not in {"api", "oop", "etl", "sql", "aws", "gcp", "cicd", "wcag"}:
                continue
            found.append(n)
            continue

    out = _dedup_keep_order(found)
    return out[:140]


# -----------------------------
# Public API
# -----------------------------
def extract_jd_structured(jd_text: str) -> dict:
    company, role = extract_company_role(jd_text)
    location = extract_location(jd_text)
    work_mode = detect_work_mode(jd_text)
    relocation_required = detect_relocation_required(jd_text)

    sections = _split_sections(jd_text)

    candidates: List[str] = []
    for key in ("must", "nice", "tools", "resp"):
        candidates.extend(_extract_candidate_lines(sections.get(key, "")))

    tech_items = _keep_only_tech(candidates)

    hard_skills = [x for x in tech_items if x in HARD_SKILLS_SET]
    role_signals = [x for x in tech_items if x in ROLE_SIGNALS_SET]
    keywords = extract_keywords_tech_only(jd_text)

    jd_signals = _dedup_keep_order(hard_skills + role_signals + keywords)

    signal_size = len(_dedup_keep_order(hard_skills + role_signals))
    signal_note = "OK"
    if signal_size < 6:
        signal_note = "LOW_SIGNAL (paste full responsibilities + requirements for best results)"

    role_level = infer_role_level(jd_text, role_title=role)

    # ✅ Compatibility keys expected by older scoring/bridge code
    must_have_skills = _dedup_keep_order(hard_skills + role_signals)[:80]
    tools_tech = _dedup_keep_order(hard_skills)[:80]
    nice_to_have_skills = []  # kept empty intentionally; we don't guess

    return {
        "company": company.strip(),
        "role_title": role.strip(),
        "job_location": location.strip(),
        "work_mode": work_mode,
        "relocation_required": relocation_required,
        "role_level": role_level,

        "hard_skills": hard_skills,
        "role_signals": role_signals,
        "jd_signals": jd_signals,
        "keywords": keywords,

        # ✅ compat keys
        "must_have_skills": must_have_skills,
        "tools_tech": tools_tech,
        "nice_to_have_skills": nice_to_have_skills,

        "signal": {
            "size": int(signal_size),
            "note": signal_note,
        },

        "summary": "JD Extract v2.5 (tech-only; adds compat keys + role level).",
    }
