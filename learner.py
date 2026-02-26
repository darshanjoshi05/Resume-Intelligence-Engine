import json
import re
from pathlib import Path
from datetime import datetime

DATA_DIR = Path("data")
LEARNED_PATH = DATA_DIR / "learned_skills.json"
ALIASES_PATH = DATA_DIR / "skill_aliases_seed.json"

# A small stoplist to avoid learning junk words
STOP = set("""
a an the and or of to in for with on at by from as is are was were be been being
requirements responsibilities experience years strong ability must should
""".split())

# Common skill-like patterns you want to capture
SKILL_PATTERNS = [
    r"\bjava\b", r"\bspring boot\b", r"\bspring\b", r"\bhibernate\b", r"\bjpa\b",
    r"\brest\b", r"\bapi\b", r"\bmicroservices?\b",
    r"\breact(\.js)?\b", r"\bjavascript\b", r"\bhtml\b", r"\bcss\b",
    r"\bpython\b", r"\bpandas\b", r"\bnumpy\b", r"\bscikit[- ]learn\b", r"\bmachine learning\b",
    r"\bsql\b", r"\bpostgresql\b", r"\bmysql\b", r"\bsql server\b", r"\boracle\b",
    r"\bmongodb\b", r"\bnosql\b",
    r"\baws\b", r"\bazure\b", r"\bdocker\b", r"\bkubernetes\b",
    r"\bgit\b", r"\btableau\b", r"\bpower bi\b"
]

def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def _save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")

def extract_skills_from_jd(jd_text: str) -> list[str]:
    t = (jd_text or "").lower()

    found = set()

    # Pattern hits
    for pat in SKILL_PATTERNS:
        m = re.findall(pat, t)
        for x in m:
            s = x if isinstance(x, str) else str(x)
            found.add(s.strip().lower())

    # Heuristic tokens (tech-ish words)
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9\.\+\-#/]{2,}", jd_text or "")
    for tok in tokens:
        low = tok.lower().strip()
        if low in STOP:
            continue
        if len(low) >= 3 and any(ch.isdigit() for ch in low) is False:
            # keep only likely tech terms
            if low in ["jira", "agile", "scrum", "ci/cd", "cicd", "oauth", "jwt"]:
                found.add(low)

    # Clean
    cleaned = sorted({f.replace(".js", "").strip() for f in found if f and f not in STOP})
    return cleaned

def update_learned_skills(jd_text: str, company: str, role_title: str) -> dict:
    DATA_DIR.mkdir(exist_ok=True)

    store = _load_json(LEARNED_PATH, {"skills": {}, "runs": []})
    skills = store.get("skills", {})
    runs = store.get("runs", [])

    extracted = extract_skills_from_jd(jd_text)

    # Update frequency + examples
    for s in extracted:
        entry = skills.get(s, {"count": 0, "examples": []})
        entry["count"] += 1
        if len(entry["examples"]) < 5:
            entry["examples"].append({"company": company, "role": role_title})
        skills[s] = entry

    runs.append({
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "company": company,
        "role": role_title,
        "extracted_count": len(extracted)
    })
    store["skills"] = skills
    store["runs"] = runs[-200:]  # cap

    _save_json(LEARNED_PATH, store)
    return {"extracted": extracted, "total_known": len(skills)}

def auto_alias_update(master: dict, extracted: list[str]) -> None:
    """
    If master has SQL and JD has postgresql -> add alias mapping.
    Similar for react/reactjs.
    """
    aliases = _load_json(ALIASES_PATH, {})

    master_skills_flat = set()
    skills = master.get("skills", {}) or {}
    for _, items in skills.items():
        if isinstance(items, list):
            for it in items:
                master_skills_flat.add(str(it).lower())

    def add_alias(base: str, alias: str):
        base_key = base
        cur = aliases.get(base_key, [])
        if alias not in cur:
            cur.append(alias)
        aliases[base_key] = sorted(set(cur))

    # Rules
    if "sql" in master_skills_flat and "postgresql" in extracted:
        add_alias("SQL", "PostgreSQL")
    if "reactjs" in master_skills_flat and "react" in extracted:
        add_alias("ReactJS", "React")

    _save_json(ALIASES_PATH, aliases)
