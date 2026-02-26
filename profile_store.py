import json
import re
from pathlib import Path
from typing import Any, Dict, List

DATA_DIR = Path("data")
MASTER_PATH = DATA_DIR / "master_profile.json"
BACKUP_DIR = DATA_DIR / "backups"

DEFAULT_PROFILE = {
    "basics": {
        "name": "",
        "email": "",
        "phone": "",
        "linkedin": "",
        "location": "",
        "open_to_relocation": True,
    },
    "summary": "",
    "skills": {
        "Programming": [],
        "Web & Frontend": [],
        "Data & Databases": [],
        "Data Analysis & ML": [],
        "Tools": [],
    },
    "experience": [],
    "projects": [],
    "education": [],
    "publications": [],
}

def _deepcopy(d: dict) -> dict:
    return json.loads(json.dumps(d))

def _ensure_file():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not MASTER_PATH.exists():
        MASTER_PATH.write_text(json.dumps(DEFAULT_PROFILE, indent=2), encoding="utf-8")

def _normalize_profile(d: dict) -> dict:
    out = _deepcopy(DEFAULT_PROFILE)
    if isinstance(d, dict):
        out.update(d)

    if isinstance((d or {}).get("basics"), dict):
        out["basics"].update(d["basics"])

    if not (isinstance(out.get("summary"), str) and out["summary"].strip()):
        obj = (d or {}).get("objective")
        if isinstance(obj, str) and obj.strip():
            out["summary"] = obj.strip()

    if isinstance((d or {}).get("skills"), dict):
        out["skills"].update(d["skills"])

    for k in ["experience", "projects", "education", "publications"]:
        v = (d or {}).get(k, [])
        out[k] = list(v or []) if isinstance(v, list) else []

    for cat, items in (out.get("skills") or {}).items():
        if isinstance(items, str):
            out["skills"][cat] = [x.strip() for x in items.split(",") if x.strip()]
        elif isinstance(items, list):
            out["skills"][cat] = [str(x).strip() for x in items if str(x).strip()]
        else:
            out["skills"][cat] = []

    out["basics"]["open_to_relocation"] = bool(out["basics"].get("open_to_relocation", True))
    return out

def load_profile() -> dict:
    _ensure_file()
    try:
        d = json.loads(MASTER_PATH.read_text(encoding="utf-8"))
    except Exception:
        d = _deepcopy(DEFAULT_PROFILE)
    return _normalize_profile(d)

def _rotate_backups(max_keep: int = 20):
    if not BACKUP_DIR.exists():
        return
    files = sorted(BACKUP_DIR.glob("master_profile_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for p in files[max_keep:]:
        try:
            p.unlink()
        except Exception:
            pass

def backup_profile() -> None:
    _ensure_file()
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    from datetime import datetime
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"master_profile_{stamp}.json"
    try:
        backup_path.write_text(MASTER_PATH.read_text(encoding="utf-8"), encoding="utf-8")
        _rotate_backups(20)
    except Exception:
        pass

def save_profile(profile: dict) -> None:
    backup_profile()
    MASTER_PATH.parent.mkdir(parents=True, exist_ok=True)
    normalized = _normalize_profile(profile if isinstance(profile, dict) else {})
    MASTER_PATH.write_text(json.dumps(normalized, indent=2), encoding="utf-8")

def merge_save_profile(patch: dict) -> dict:
    base = load_profile()
    if not isinstance(patch, dict):
        return base

    if isinstance(patch.get("basics"), dict):
        base.setdefault("basics", {})
        base["basics"].update(patch["basics"])

    if isinstance(patch.get("summary"), str):
        base["summary"] = patch["summary"]

    if isinstance(patch.get("skills"), dict):
        base.setdefault("skills", {})
        for cat, items in patch["skills"].items():
            base["skills"][cat] = items

    for k in ("experience", "projects", "education", "publications"):
        if k in patch:
            base[k] = patch[k] if isinstance(patch[k], list) else []

    save_profile(base)
    return load_profile()

def skills_to_text(skills: dict) -> dict:
    return {cat: ", ".join(items or []) for cat, items in (skills or {}).items()}

def parse_skill_csv(text: str) -> list[str]:
    if not text:
        return []
    parts = re.split(r"[,\n;]+", text)
    return sorted({p.strip() for p in parts if p.strip()}, key=str.lower)

def parse_experience_block(text: str) -> list[dict]:
    if not (text or "").strip():
        return []
    blocks = re.split(r"\n\s*\n+", text.strip())
    out = []
    for b in blocks:
        lines = [l.rstrip() for l in b.splitlines() if l.strip()]
        if not lines:
            continue
        parts = [p.strip() for p in lines[0].split("|")]
        while len(parts) < 5:
            parts.append("")
        title, company, location, start, end = parts[:5]
        bullets = []
        for l in lines[1:]:
            l = l.strip()
            bullets.append(l[1:].strip() if l.startswith("-") else l)
        out.append({
            "title": title,
            "company": company,
            "location": location,
            "start": start,
            "end": end,
            "bullets": [x for x in bullets if x],
        })
    return out

def parse_projects_block(text: str) -> list[dict]:
    if not (text or "").strip():
        return []
    blocks = re.split(r"\n\s*\n+", text.strip())
    out = []
    for b in blocks:
        lines = [l.rstrip() for l in b.splitlines() if l.strip()]
        if not lines:
            continue
        parts = [p.strip() for p in lines[0].split("|")]
        while len(parts) < 4:
            parts.append("")
        name, org, dates, tags = parts[:4]
        tag_list = [t.strip() for t in re.split(r"[,;]+", tags) if t.strip()]
        bullets = []
        for l in lines[1:]:
            l = l.strip()
            bullets.append(l[1:].strip() if l.startswith("-") else l)
        out.append({
            "name": name,
            "org": org,
            "dates": dates,
            "tags": tag_list,
            "bullets": [x for x in bullets if x],
        })
    return out

def parse_education_lines(text: str) -> list[dict]:
    if not (text or "").strip():
        return []
    out = []
    for line in text.strip().splitlines():
        if not line.strip():
            continue
        parts = [p.strip() for p in line.split("|")]
        while len(parts) < 3:
            parts.append("")
        degree, school, dates = parts[:3]
        out.append({"degree": degree, "school": school, "dates": dates})
    return out

def parse_publication_lines(text: str) -> list[dict]:
    if not (text or "").strip():
        return []
    out = []
    for line in text.strip().splitlines():
        if not line.strip():
            continue
        parts = [p.strip() for p in line.split("|")]
        while len(parts) < 4:
            parts.append("")
        title, venue, pub_date, link = parts[:4]
        out.append({"title": title, "venue": venue, "date": pub_date, "link": link})
    return out

def experience_to_block(experience: list[dict]) -> str:
    if not isinstance(experience, list) or not experience:
        return ""
    blocks = []
    for e in experience:
        if not isinstance(e, dict):
            continue
        title = (e.get("title") or "").strip()
        company = (e.get("company") or e.get("org") or "").strip()
        location = (e.get("location") or "").strip()
        start = (e.get("start") or "").strip()
        end = (e.get("end") or "").strip()

        header = " | ".join([title, company, location, start, end]).rstrip()
        lines = [header] if header.strip() else []

        for b in (e.get("bullets") or []):
            b = str(b).strip()
            if b:
                lines.append(f"- {b}")

        if lines:
            blocks.append("\n".join(lines))

    return "\n\n".join(blocks)

def projects_to_block(projects: list[dict]) -> str:
    if not isinstance(projects, list) or not projects:
        return ""
    blocks = []
    for p in projects:
        if not isinstance(p, dict):
            continue

        name = (p.get("name") or "").strip()
        org = (p.get("org") or p.get("company") or "").strip()
        dates = (p.get("dates") or "").strip()

        tech = (p.get("tech") or "").strip()
        tags = p.get("tags") or []
        if (not tech) and isinstance(tags, list):
            tech = ", ".join([str(t).strip() for t in tags if str(t).strip()])
        elif (not tech) and tags:
            tech = str(tags).strip()

        header = " | ".join([name, org, dates, tech]).rstrip()
        lines = [header] if header.strip() else []

        for b in (p.get("bullets") or []):
            b = str(b).strip()
            if b:
                lines.append(f"- {b}")

        if lines:
            blocks.append("\n".join(lines))

    return "\n\n".join(blocks)

def education_to_lines(education: list[dict]) -> str:
    if not isinstance(education, list) or not education:
        return ""
    out = []
    for e in education:
        if not isinstance(e, dict):
            continue
        degree = (e.get("degree") or "").strip()
        school = (e.get("school") or "").strip()

        dates = (e.get("dates") or "").strip()
        if not dates:
            start = (e.get("start") or "").strip()
            end = (e.get("end") or "").strip()
            if start or end:
                dates = " - ".join([x for x in [start, end] if x])

        out.append(" | ".join([degree, school, dates]).rstrip())
    return "\n".join(out)

def publications_to_lines(pubs: list[dict]) -> str:
    if not isinstance(pubs, list) or not pubs:
        return ""
    out = []
    for p in pubs:
        if not isinstance(p, dict):
            continue
        title = (p.get("title") or "").strip()
        venue = (p.get("venue") or "").strip()
        dt = (p.get("date") or "").strip()
        link = (p.get("link") or "").strip()
        out.append(" | ".join([title, venue, dt, link]).rstrip())
    return "\n".join(out)
