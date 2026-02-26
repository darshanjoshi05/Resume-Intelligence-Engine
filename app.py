import json
import re
from pathlib import Path
from datetime import datetime, date, timedelta
from urllib.parse import quote

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, PlainTextResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from db import init_db, get_conn
from role_detect import detect_role_family
from jd_extract import extract_jd_structured
from skill_bridge import smart_bridge_skills
from suitability import infer_candidate_lanes, suggested_roles_from_lanes, learning_plan_from_missing

from profile_store import (
    load_profile,
    merge_save_profile,
    skills_to_text,
    parse_skill_csv,
    parse_experience_block,
    parse_projects_block,
    parse_education_lines,
    parse_publication_lines,
    experience_to_block,
    projects_to_block,
    education_to_lines,
    publications_to_lines,
)

from generator import (
    make_resume_text_blocks,
    generate_docx,
    generate_pdf_full,
    generate_cover_letter,
    recruiter_message,
)

# -----------------------------
# Paths / App Setup
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUTS_DIR = BASE_DIR / "outputs"
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

MASTER_PATH = DATA_DIR / "master_profile.json"
SETTINGS_PATH = DATA_DIR / "settings.json"

app = FastAPI()
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# -----------------------------
# Settings (single source of truth)
# -----------------------------
def load_settings() -> dict:
    """
    Loads settings.json and *migrates* older schemas safely.

    Key rule: templates can always rely on:
      settings['output'], settings['learning'], settings['targets'], settings['ui']
    """
    defaults = {
        "targets": {"daily": 3, "weekly": 15},
        "output": {
            "default_role": "frontend",     # frontend | fullstack | backend | data
            "resume_length": "1_page",      # 1_page | 2_pages
            "keyword_mode": "balanced",     # safe | balanced | aggressive
            "summary_mode": "dynamic_with_override",  # dynamic_with_override | always_dynamic | always_custom
            "section_order": ["SUMMARY","EDUCATION","SKILLS","EXPERIENCE","PROJECTS","CERTIFICATIONS","PUBLICATIONS"],
        },
        "learning": {
            "enabled": True,
            "confidence_threshold": 0.62,   # 0..1
            "learn_from_jds": True,
        },
        "ui": {"accent": "light_orange"},
        # legacy keys we still tolerate
        "nxtwave": {"course": "", "current_topic": "", "streak_days": 0},
        "openai_model": "gpt-5-mini",
    }

    def _deep_merge(dst: dict, src: dict) -> dict:
        for k, v in (src or {}).items():
            if isinstance(v, dict) and isinstance(dst.get(k), dict):
                dst[k] = _deep_merge(dict(dst.get(k) or {}), v)
            else:
                dst[k] = v
        return dst

    loaded = {}
    if SETTINGS_PATH.exists():
        try:
            loaded = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except Exception:
            loaded = {}

    if not isinstance(loaded, dict):
        loaded = {}

    merged = _deep_merge(dict(defaults), loaded)

    # clamp learning confidence 0..1
    try:
        ct = float((merged.get("learning") or {}).get("confidence_threshold", 0.62))
        if ct < 0: ct = 0.0
        if ct > 1: ct = 1.0
        merged.setdefault("learning", {})
        merged["learning"]["confidence_threshold"] = ct
    except Exception:
        merged.setdefault("learning", {})
        merged["learning"]["confidence_threshold"] = 0.62

    # make sure required dicts exist
    for must in ("targets", "output", "learning", "ui"):
        if not isinstance(merged.get(must), dict):
            merged[must] = dict(defaults[must])

    # auto-migrate: if file missing required keys, write back so it stops breaking
    try:
        if merged != loaded:
            save_settings(merged)
    except Exception:
        pass

    return merged


def save_settings(s: dict) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(s, indent=2), encoding="utf-8")

def _common_context() -> dict:
    # unread_notification_count is optional: don't let UI crash
    try:
        from db import unread_notification_count
        n = unread_notification_count()
    except Exception:
        n = 0
    return {"notif_count": n, "settings": load_settings()}

def _is_truthy(v) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    s = str(v).strip().lower()
    return s in ("1", "true", "yes", "y", "on")

# -----------------------------
# Startup
# -----------------------------
@app.on_event("startup")
def _startup():
    DATA_DIR.mkdir(exist_ok=True)
    OUTPUTS_DIR.mkdir(exist_ok=True)
    init_db()

# -----------------------------
# Safe file serving
# -----------------------------
def _safe_resolve_outputs(path_str: str) -> Path | None:
    try:
        p = Path(path_str)
        if not p.is_absolute():
            p = (BASE_DIR / p).resolve()
        else:
            p = p.resolve()

        out = OUTPUTS_DIR.resolve()
        if str(p).startswith(str(out)) and p.exists() and p.is_file():
            return p
    except Exception:
        pass
    return None

# -----------------------------
# Text sanitization
# -----------------------------
def _sanitize_text(s: str) -> str:
    if s is None:
        return ""
    s = str(s)

    # remove control chars (except newline/tab)
    s = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", s)

    # remove common replacement/bad glyphs
    s = s.replace("\uFFFD", "")  # replacement char
    s = s.replace("\u25A0", "")  # black square ■

    # remove zero-width chars
    s = s.replace("\u200b", "").replace("\u200c", "").replace("\u200d", "")

    return s.strip()

# -----------------------------
# Effective Profile
# -----------------------------
def load_master() -> dict:
    """
    Single source of truth: data/master_profile.json.
    profile_store ensures it exists and is normalized.
    """
    return load_profile()

def _effective_profile() -> dict:
    """
    Single source of truth: master_profile.json only.
    Normalizes legacy/duplicate keys so the rest of the app sees a consistent structure:
      - contact fields live inside basics
      - summary is stored as 'summary' (falls back to objective)
      - top-level duplicates are removed/ignored
    """
    master = load_master() or {}
    if not isinstance(master, dict):
        master = {}

    basics = master.get("basics") if isinstance(master.get("basics"), dict) else {}
    basics = dict(basics)

    def _boolish(v, default=True):
        if isinstance(v, bool):
            return v
        if v is None:
            return default
        s = str(v).strip().lower()
        if s in ("1", "true", "yes", "y", "on"):
            return True
        if s in ("0", "false", "no", "n", "off"):
            return False
        return default

    # normalize contact fields into basics
    for k in ("name", "email", "phone", "linkedin", "location"):
        v = basics.get(k)
        if not (isinstance(v, str) and v.strip()):
            rv = master.get(k)
            if isinstance(rv, str) and rv.strip():
                basics[k] = rv.strip()

    # relocation flags
    if "open_to_relocation" in basics:
        basics["open_to_relocation"] = _boolish(basics.get("open_to_relocation"), default=True)
    elif "open_to_relocation" in master:
        basics["open_to_relocation"] = _boolish(master.get("open_to_relocation"), default=True)
    elif "relocation" in master:
        basics["open_to_relocation"] = _boolish(master.get("relocation"), default=True)
    else:
        basics["open_to_relocation"] = True

    # summary normalization
    summary = master.get("summary")
    if not (isinstance(summary, str) and summary.strip()):
        obj = master.get("objective")
        summary = obj.strip() if isinstance(obj, str) and obj.strip() else ""
    else:
        summary = summary.strip()

    eff = dict(master)
    eff["basics"] = basics
    eff["summary"] = summary

    # remove duplicate root keys
    for k in ("name", "email", "phone", "linkedin", "location", "relocation", "open_to_relocation"):
        eff.pop(k, None)

    return eff

# -----------------------------
# Term normalization + noise filter
# -----------------------------
_NOISE_TERMS = {
    "benefit", "benefits", "insurance", "medical", "dental", "vision", "401k", "pto",
    "equal opportunity", "eeo", "salary", "compensation", "background check", "drug test",
    "accommodation", "reasonable accommodation", "privacy", "cookie", "terms of use",
    "tuition reimbursement", "fitness reimbursement", "safety shoe", "protective eyewear",
    "country/region", "hours/week", "work authorization", "e-verify", "sponsorship",
    "fluent english", "english communication", "communication skills",
    "strong math skills", "math skills", "stakeholders", "additional duties",
    "team meetings", "coordinate tasks", "documentation",
}

_CANON = {
    "reactjs": "react",
    "react.js": "react",
    "rest concepts": "rest",
    "restful": "rest",
    "apis": "api",
    "oop": "object oriented",
    "object-oriented": "object oriented",
    "object oriented programming": "object oriented",
    "relational databases": "relational database",
    "mssql": "sql server",
    "ms sql": "sql server",
    "sqlserver": "sql server",
    "jupyter notebook": "jupyter",
}

def _norm_term(t: str) -> str:
    s = (t or "").strip().lower()
    s = s.replace("•", " ").replace("·", " ").replace("—", "-").replace("–", "-")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _canon_term(t: str) -> str:
    s = _norm_term(t)
    s = s.replace("—", "-").replace("–", "-")
    s = s.replace("object-oriented", "object oriented")
    return _CANON.get(s, s)

def _is_noise_term(t: str) -> bool:
    if not t:
        return True
    tl = _norm_term(t)
    if len(tl) <= 1:
        return True
    if "http://" in tl or "https://" in tl or "www." in tl:
        return True
    if re.search(r"\b[a-z0-9\-]+\.(com|org|net|io|ai|edu)\b", tl):
        return True
    for bad in _NOISE_TERMS:
        if bad in tl:
            return True
    return False

def _has_tech_cue(t: str) -> bool:
    tl = (t or "").lower()
    if re.search(r"[+#./]", tl):
        return True
    if re.search(r"\b(c\+\+|c#|\.net|asp\.net|java|python|javascript|typescript|sql|api|rest|oop)\b", tl):
        return True
    if re.search(r"\b(visual studio|windows server|mssql|sql server|git|subversion|docker|aws|azure)\b", tl):
        return True
    return False

def _is_noise_missing_term(term: str) -> bool:
    if not term:
        return True
    t = term.strip()
    tl = t.lower()
    if "http://" in tl or "https://" in tl or "www." in tl:
        return True
    if re.search(r"\b[a-z0-9\-]+\.(com|org|net|io|ai|edu)\b", tl):
        return True
    if len(t) > 80 and not _has_tech_cue(t):
        return True
    for bad in _NOISE_TERMS:
        if bad in tl:
            return True
    if len(tl) <= 2:
        return True
    return False

def _dedup_keep_order(xs: list[str]) -> list[str]:
    out, seen = [], set()
    for x in xs:
        k = _norm_term(x)
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(k)
    return out

# -----------------------------
# Scoring helpers
# -----------------------------
def _profile_skill_set(master: dict) -> set[str]:
    skills = set()

    ms = master.get("skills", {}) or {}
    if isinstance(ms, dict):
        for _, arr in ms.items():
            if isinstance(arr, list):
                for x in arr:
                    k = _canon_term(str(x))
                    if k:
                        skills.add(k)
            else:
                k = _canon_term(str(arr))
                if k:
                    skills.add(k)
    elif isinstance(ms, list):
        for x in ms:
            k = _canon_term(str(x))
            if k:
                skills.add(k)

    for k in ("summary", "headline"):
        v = master.get(k)
        if isinstance(v, str):
            for tok in re.findall(r"[A-Za-z][A-Za-z0-9\.\+#/]{1,}", v):
                skills.add(_canon_term(tok))

    return {s for s in skills if s and not _is_noise_term(s)}

def _jd_signal_terms(jd_struct: dict) -> list[str]:
    if not isinstance(jd_struct, dict):
        return []

    primary = jd_struct.get("jd_signals", []) or []
    if isinstance(primary, list) and len(primary) >= 6:
        clean = []
        for x in primary:
            s = _canon_term(str(x))
            if not s or _is_noise_term(s):
                continue
            clean.append(s)
        return _dedup_keep_order(clean)[:60]

    must_ = jd_struct.get("must_have_skills", []) or []
    tools = jd_struct.get("tools_tech", []) or []
    nice_ = jd_struct.get("nice_to_have_skills", []) or []

    raw = list(must_) + list(tools) + list(nice_)
    clean: list[str] = []
    for x in raw:
        s = _canon_term(str(x))
        if not s or _is_noise_term(s):
            continue
        clean.append(s)
    clean = _dedup_keep_order(clean)

    if len(clean) < 8:
        kw = jd_struct.get("keywords", []) or []
        for x in kw:
            s = _canon_term(str(x))
            if not s or _is_noise_term(s):
                continue
            clean.append(s)
        clean = _dedup_keep_order(clean)

    return clean[:60]

def _smart_bridge(profile: dict, jd_text: str, jd_struct: dict) -> dict:
    try:
        return smart_bridge_skills(profile, jd_text, jd_struct=jd_struct)
    except TypeError:
        return smart_bridge_skills(profile, jd_text)

def _compute_match_score_v3(master: dict, jd_struct: dict, bridge_info: dict) -> dict:
    profile = _profile_skill_set(master)
    jd_terms = _jd_signal_terms(jd_struct)

    note = "LOW_SIGNAL: paste full responsibilities + requirements for meaningful score." if len(jd_terms) < 6 else "OK"

    matched = [t for t in jd_terms if t in profile]

    bridged: list[str] = []
    bridges = bridge_info.get("bridges", []) or []
    for b in bridges:
        if isinstance(b, str):
            bridged.append(_norm_term(b))
        elif isinstance(b, dict):
            for key in ("to", "target", "term", "skill"):
                if b.get(key):
                    bridged.append(_norm_term(str(b[key])))
                    break
    bridged = [x for x in bridged if x and not _is_noise_term(x)]

    matched_set = set(matched)
    bridged_set = set(bridged)

    missing = [t for t in jd_terms if (t not in matched_set and t not in bridged_set)]
    missing = [m for m in missing if not _is_noise_missing_term(m)]
    missing = [m for m in missing if _has_tech_cue(m) or len(m) <= 28]
    missing = missing[:25]

    denom = max(8, len(jd_terms))
    raw = (len(matched) + 0.5 * len(bridged_set)) / denom
    score = round(min(100.0, max(0.0, raw * 100.0)), 1)

    return {
        "score": score,
        "matched_terms": matched,
        "bridged_terms": sorted(list(bridged_set)),
        "missing_terms": missing,
        "jd_signal_size": len(jd_terms),
        "note": note,
        "debug": {
            "profile_skill_count": len(profile),
            "jd_term_count": len(jd_terms),
        },
    }

def _recruiter_variants(profile: dict, company: str, role_title: str) -> list[str]:
    base = recruiter_message(profile, company, role_title) or ""
    name = (profile.get("basics", {}) or {}).get("name", "") or "Darshan"

    v0 = base.strip() if base.strip() else f"Hi {company} team — I'm {name}. I applied for {role_title} and would love to connect."
    v1 = f"Hi {company} team — I applied for {role_title}. I’m strong in the core fundamentals and can share a couple relevant projects. Open to a quick chat?"
    v2 = f"Hello {company} recruiters — I’m reaching out about {role_title}. If helpful, I can send a short portfolio snapshot aligned to your JD. Thanks!"
    return [v0, v1, v2]

def _slug(s: str) -> str:
    s = (s or "").strip()
    s = "".join([c for c in s if c.isalnum() or c in (" ", "-", "_")]).strip()
    return s.replace(" ", "_") or "Unknown"

# -----------------------------
# Home
# -----------------------------
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    conn = get_conn()
    cur = conn.cursor()

    # totals
    cur.execute("SELECT COUNT(*), AVG(match_score) FROM applications")
    row = cur.fetchone() or (0, 0)
    total, avg_match = int(row[0] or 0), float(row[1] or 0)

    # today
    today_str = date.today().strftime("%Y-%m-%d")
    cur.execute("SELECT COUNT(*) FROM applications WHERE created_at LIKE ?", (today_str + "%",))
    today_count = int((cur.fetchone() or [0])[0] or 0)

    # last 7 days
    start = (date.today() - timedelta(days=6)).strftime("%Y-%m-%d")
    cur.execute("SELECT COUNT(*) FROM applications WHERE created_at >= ?", (start,))
    week_count = int((cur.fetchone() or [0])[0] or 0)

    # followups due today (optional column)
    due_today = 0
    try:
        cur.execute("SELECT COUNT(*) FROM applications WHERE followup_date = ?", (today_str,))
        due_today = int((cur.fetchone() or [0])[0] or 0)
    except Exception:
        due_today = 0

    conn.close()

    stats = {
        "total": total,
        "today": today_count,
        "week": week_count,
        "avg_match": round(avg_match, 1),
        "due_today": due_today,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    # templates use safe defaults if insights is missing
    ctx = {"request": request, "title": "Home", "stats": stats, "insights": {}}
    ctx.update(_common_context())
    return templates.TemplateResponse("home.html", ctx)

# -----------------------------
# Create page
# -----------------------------
@app.get("/new", response_class=HTMLResponse)
def new_app(request: Request):
    ctx = {"request": request, "title": "Create"}
    ctx.update(_common_context())
    return templates.TemplateResponse("new.html", ctx)

# -----------------------------
# Generate + Track (core pipeline)
# -----------------------------
@app.post("/generate")
def generate(
    request: Request,
    company: str = Form(""),
    role_title: str = Form(""),
    jd_text: str = Form(...),
):
    jd_text = _sanitize_text(jd_text)
    company = _sanitize_text(company) or "Unknown"
    role_title = _sanitize_text(role_title) or "Unknown Role"

    role_family = detect_role_family(jd_text) or ""

    profile = _effective_profile()
    jd_struct = extract_jd_structured(jd_text)
    bridge_info = _smart_bridge(profile, jd_text, jd_struct)
    score_pack = _compute_match_score_v3(profile, jd_struct, bridge_info)

    # learning plan + suggested roles
    lanes = infer_candidate_lanes(profile)
    suggested = suggested_roles_from_lanes(lanes) if lanes else []
    learn_plan = learning_plan_from_missing(score_pack.get("missing_terms") or [])

    report = {
        "profile_snapshot": profile,
        "jd_extract": jd_struct,
        "bridge_info": bridge_info,
        "score_breakdown": score_pack,
        "matched_skills": score_pack.get("matched_terms", []),
        "missing_terms": score_pack.get("missing_terms", []),
        "bridges": bridge_info.get("bridges", []) if isinstance(bridge_info, dict) else [],
        "learning_plan": learn_plan or [],
        "suggested_roles": suggested or [],
        "recruiter_variants": _recruiter_variants(profile, company, role_title),
    }

    match_score = float(score_pack.get("score") or 0)
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    conn = get_conn()
    cur = conn.cursor()

    # Insert, tolerant of schema differences
    app_id = None
    try:
        cur.execute(
            """
            INSERT INTO applications
            (company, role_title, role_family, jd_text, match_score, created_at, report_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (company, role_title, role_family, jd_text, match_score, created_at, json.dumps(report, indent=2)),
        )
        app_id = cur.lastrowid
    except Exception:
        # fallback with more columns if your schema has them
        cur.execute(
            """
            INSERT INTO applications
            (company, role_title, role_family, jd_text, match_score, created_at,
             job_location, work_mode, relocation_required,
             status, followup_date,
             resume_docx_path, resume_pdf_path, cover_letter_path,
             recruiter_msg, report_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                company, role_title, role_family, jd_text, match_score, created_at,
                "", "UNKNOWN", 0,
                "APPLIED", "",
                "", "", "",
                report["recruiter_variants"][0] if report["recruiter_variants"] else "",
                json.dumps(report, indent=2),
            ),
        )
        app_id = cur.lastrowid

    conn.commit()
    conn.close()

    return RedirectResponse(url=f"/application/{app_id}", status_code=303)

# -----------------------------
# Applications list
# -----------------------------
@app.get("/applications", response_class=HTMLResponse)
def applications(request: Request):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            id,
            company,
            role_title,
            role_family,
            created_at,
            job_location,
            work_mode,
            match_score,
            resume_pdf_path,
            resume_docx_path,
            cover_letter_path
        FROM applications
        ORDER BY id DESC
        LIMIT 400
        """
    )
    rows = cur.fetchall()
    conn.close()

    apps = []
    for r in rows:
        created_at = r[4] or ""
        created_date = created_at.split(" ")[0] if created_at else ""

        formatted_date = created_date
        try:
            dt = datetime.strptime(created_date, "%Y-%m-%d")
            formatted_date = dt.strftime("%d-%m-%y")
        except Exception:
            pass

        apps.append(
            {
                "id": r[0],
                "company": r[1] or "Unknown",
                "role_title": r[2] or "Unknown Role",
                "role_family": r[3] or "",
                "created_date": formatted_date,
                "job_location": r[5] or "—",
                "work_mode": r[6] or "UNKNOWN",
                "match_score": round(float(r[7] or 0), 1),
                "resume_pdf_path": r[8] or "",
                "resume_docx_path": r[9] or "",
                "cover_letter_path": r[10] or "",
            }
        )

    ctx = {"request": request, "title": "Applications", "apps": apps}
    ctx.update(_common_context())
    return templates.TemplateResponse("applications.html", ctx)

# -----------------------------
# Application detail
# -----------------------------
@app.get("/application/{app_id}", response_class=HTMLResponse)
def application_detail(request: Request, app_id: int):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            id, company, role_title, role_family, jd_text, match_score, created_at,
            job_location, work_mode, relocation_required,
            status, followup_date,
            resume_docx_path, resume_pdf_path, cover_letter_path,
            recruiter_msg, report_json
        FROM applications
        WHERE id = ?
        LIMIT 1
        """,
        (app_id,),
    )
    row = cur.fetchone()
    conn.close()

    if not row:
        return PlainTextResponse("Application not found.", status_code=404)

    app_obj = {
        "id": row[0],
        "company": row[1] or "Unknown",
        "role_title": row[2] or "Unknown Role",
        "role_family": row[3] or "",
        "jd_text": row[4] or "",
        "match_score": round(float(row[5] or 0), 1),
        "created_at": row[6] or "",
        "job_location": row[7] or "",
        "work_mode": row[8] or "UNKNOWN",
        "relocation_required": bool(row[9] or 0),
        "status": row[10] or "APPLIED",
        "followup_date": row[11] or "",
        "resume_docx_path": row[12] or "",
        "resume_pdf_path": row[13] or "",
        "cover_letter_path": row[14] or "",
        "recruiter_msg": row[15] or "",
    }

    report_raw = row[16] or "{}"
    try:
        report = json.loads(report_raw)
        if not isinstance(report, dict):
            report = {}
    except Exception:
        report = {}

    # Resume preview blocks (NO file generation)
    profile = _effective_profile()
    jd_struct = report.get("jd_extract") or extract_jd_structured(app_obj["jd_text"])
    try:
        preview_blocks = make_resume_text_blocks(
            profile,
            app_obj.get("role_family", "") or "",
            bridge_info={},  # preview doesn't need bridging
            jd_text=app_obj.get("jd_text", ""),
            template_sections=None,
            selected_projects=None,
            jd_struct=jd_struct,
        )
    except Exception:
        preview_blocks = {}

    # Keep UI keys stable
    report.setdefault("matched_skills", report.get("matched_skills", []) or [])
    report.setdefault("missing_terms", report.get("missing_terms", []) or [])
    report.setdefault("recruiter_variants", report.get("recruiter_variants", []) or [])
    report.setdefault("learning_plan", report.get("learning_plan", []) or [])
    report.setdefault("suggested_roles", report.get("suggested_roles", []) or [])

    ctx = {
        "request": request,
        "title": f"{app_obj['company']} — {app_obj['role_title']}",
        "app": app_obj,
        "report": report,
        "preview": preview_blocks,
    }
    ctx.update(_common_context())
    return templates.TemplateResponse("application_detail.html", ctx)

# -----------------------------
# Debug scoring snapshot
# -----------------------------
@app.post("/debug/score")
def debug_score(jd_text: str = Form(...)):
    profile = _effective_profile()
    jd_text = _sanitize_text(jd_text)
    jd_struct = extract_jd_structured(jd_text)
    bridge_info = _smart_bridge(profile, jd_text, jd_struct)
    score_pack = _compute_match_score_v3(profile, jd_struct, bridge_info)
    return JSONResponse(score_pack)

# -----------------------------
# On-demand PDF generation
# -----------------------------
@app.get("/application/{app_id}/pdf")
def ensure_pdf(app_id: int):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            id, company, role_title, role_family, jd_text, resume_pdf_path, resume_docx_path, report_json
        FROM applications
        WHERE id = ?
        LIMIT 1
        """,
        (app_id,),
    )
    row = cur.fetchone()

    if not row:
        conn.close()
        return PlainTextResponse("Application not found.", status_code=404)

    _id, company, role_title, role_family, jd_text, pdf_path, docx_path, report_raw = row
    company = company or "Unknown"
    role_title = role_title or "Unknown Role"
    role_family = role_family or detect_role_family(jd_text or "")

    # If PDF already exists and is accessible -> show it
    if pdf_path:
        safe = _safe_resolve_outputs(pdf_path)
        if safe:
            conn.close()
            return RedirectResponse(url=f"/view-pdf?path={quote(str(pdf_path))}", status_code=303)

    # Load report_json to reuse snapshot (stable output)
    try:
        report = json.loads(report_raw or "{}")
        if not isinstance(report, dict):
            report = {}
    except Exception:
        report = {}

    profile_snapshot = report.get("profile_snapshot")
    if isinstance(profile_snapshot, dict) and profile_snapshot:
        profile = profile_snapshot
    else:
        profile = _effective_profile()

    jd_text = jd_text or ""
    jd_struct = report.get("jd_extract")
    if not isinstance(jd_struct, dict) or not jd_struct:
        jd_struct = extract_jd_structured(jd_text)

    bridge_info = report.get("bridge_info")
    if not isinstance(bridge_info, dict) or not bridge_info:
        bridge_info = _smart_bridge(profile, jd_text, jd_struct)

    out_name = f"{app_id}_{_slug(company)}_{_slug(role_title)}"
    new_pdf_path = str(generate_pdf_full(profile, role_family, bridge_info, jd_text, out_name, jd_struct=jd_struct))

    # Update DB
    cur.execute("UPDATE applications SET resume_pdf_path = ? WHERE id = ?", (new_pdf_path, app_id))
    report["resume_pdf_path"] = new_pdf_path
    cur.execute("UPDATE applications SET report_json = ? WHERE id = ?", (json.dumps(report, indent=2), app_id))

    conn.commit()
    conn.close()

    return RedirectResponse(url=f"/view-pdf?path={quote(new_pdf_path)}", status_code=303)

# -----------------------------
# Recruiter message actions
# -----------------------------
@app.post("/application/{app_id}/recruiter/regenerate")
def recruiter_regenerate(app_id: int):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT company, role_title, report_json FROM applications WHERE id = ? LIMIT 1", (app_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return RedirectResponse(url=f"/application/{app_id}", status_code=303)

    company = row[0] or "Unknown"
    role_title = row[1] or "Unknown Role"
    try:
        report = json.loads(row[2] or "{}")
        if not isinstance(report, dict):
            report = {}
    except Exception:
        report = {}

    profile = _effective_profile()
    variants = _recruiter_variants(profile, company, role_title)
    report["recruiter_variants"] = variants

    cur.execute(
        "UPDATE applications SET recruiter_msg = ?, report_json = ? WHERE id = ?",
        (variants[0], json.dumps(report, indent=2), app_id),
    )
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/application/{app_id}", status_code=303)

@app.post("/application/{app_id}/recruiter/use")
def recruiter_use(app_id: int, variant_index: int = Form(0)):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT report_json FROM applications WHERE id = ? LIMIT 1", (app_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return RedirectResponse(url=f"/application/{app_id}", status_code=303)

    try:
        report = json.loads(row[0] or "{}")
        if not isinstance(report, dict):
            report = {}
    except Exception:
        report = {}

    variants = report.get("recruiter_variants", []) or []
    try:
        idx = int(variant_index)
    except Exception:
        idx = 0

    chosen = ""
    if variants:
        idx = max(0, min(idx, len(variants) - 1))
        chosen = variants[idx]

    cur.execute("UPDATE applications SET recruiter_msg = ? WHERE id = ?", (chosen, app_id))
    conn.commit()
    conn.close()
    return RedirectResponse(url=f"/application/{app_id}", status_code=303)

# -----------------------------
# Generate outputs on demand
# -----------------------------
@app.post("/application/{app_id}/generate-resume")
def generate_resume_for_app(app_id: int):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT company, role_title, role_family, jd_text, report_json
        FROM applications WHERE id = ? LIMIT 1
        """,
        (app_id,),
    )
    row = cur.fetchone()
    if not row:
        conn.close()
        return RedirectResponse(url="/applications", status_code=303)

    company, role_title, role_family, jd_text, report_raw = row
    try:
        report = json.loads(report_raw or "{}")
        if not isinstance(report, dict):
            report = {}
    except Exception:
        report = {}

    profile = _effective_profile()
    jd_text = jd_text or ""
    jd_struct = report.get("jd_extract") or extract_jd_structured(jd_text)
    bridge_info = report.get("bridge_info") or _smart_bridge(profile, jd_text, jd_struct)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_name = f"{stamp}_{_slug(company)}_{_slug(role_title)}"

    docx_path = str(generate_docx(profile, role_family or "", bridge_info, jd_text, out_name, jd_struct=jd_struct))
    pdf_path = str(generate_pdf_full(profile, role_family or "", bridge_info, jd_text, out_name, jd_struct=jd_struct))

    cur.execute(
        """
        UPDATE applications
        SET resume_docx_path = ?, resume_pdf_path = ?
        WHERE id = ?
        """,
        (docx_path, pdf_path, app_id),
    )
    conn.commit()
    conn.close()

    return RedirectResponse(url=f"/application/{app_id}", status_code=303)

@app.post("/application/{app_id}/generate-cover")
def generate_cover_for_app(app_id: int):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT company, role_title FROM applications WHERE id = ? LIMIT 1", (app_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return RedirectResponse(url="/applications", status_code=303)

    company, role_title = row
    profile = _effective_profile()

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_name = f"{stamp}_{_slug(company)}_{_slug(role_title)}"
    cover_path = str(generate_cover_letter(profile, company or "Unknown", role_title or "Unknown Role", out_name))

    cur.execute("UPDATE applications SET cover_letter_path = ? WHERE id = ?", (cover_path, app_id))
    conn.commit()
    conn.close()

    return RedirectResponse(url=f"/application/{app_id}", status_code=303)

# -----------------------------
# PDF preview + download
# -----------------------------
@app.get("/view-pdf", response_class=HTMLResponse)
def view_pdf(request: Request, path: str):
    safe = _safe_resolve_outputs(path)
    if not safe:
        return PlainTextResponse("File not found (or blocked path).", status_code=404)

    encoded = quote(str(safe))
    ctx = {"request": request, "title": "PDF Preview", "path": str(safe), "path_q": encoded, "filename": safe.name}
    ctx.update(_common_context())
    return templates.TemplateResponse("view_pdf.html", ctx)

@app.get("/pdf-inline")
def pdf_inline(path: str):
    p = _safe_resolve_outputs(path)
    if not p:
        return PlainTextResponse("File not found (or blocked path).", status_code=404)
    headers = {"Content-Disposition": f'inline; filename="{p.name}"'}
    return FileResponse(p, media_type="application/pdf", headers=headers)

@app.get("/download")
def download(path: str):
    p = _safe_resolve_outputs(path)
    if not p:
        return PlainTextResponse("File not found (or blocked path).", status_code=404)
    return FileResponse(p, filename=p.name)

# -----------------------------
# Settings routes (split pages)
# -----------------------------
@app.get("/settings")
def settings_root():
    return RedirectResponse(url="/settings/profile", status_code=303)

@app.get("/settings/profile", response_class=HTMLResponse)
def settings_profile(request: Request, saved: int = 0, error: str = ""):
    p = load_profile()
    s = load_settings()
    ctx = {
        "request": request,
        "title": "Profile",
        "tab": "profile",
        "saved": bool(saved),
        "error": error,
        "p": p,
        "settings": s,
        "skills_text": skills_to_text(p.get("skills") or {}),
        "experience_block": experience_to_block(p.get("experience") or []),
        "projects_block": projects_to_block(p.get("projects") or []),
        "education_lines": education_to_lines(p.get("education") or []),
        "publication_lines": publications_to_lines(p.get("publications") or []),
    }
    ctx.update(_common_context())
    return templates.TemplateResponse("settings_profile.html", ctx)

@app.post("/settings/profile/save")
def settings_profile_save(
    name: str = Form(""),
    email: str = Form(""),
    phone: str = Form(""),
    linkedin: str = Form(""),
    location: str = Form(""),
    open_to_relocation: str = Form("false"),
    summary: str = Form(""),
    skills_programming: str = Form(""),
    skills_web: str = Form(""),
    skills_data: str = Form(""),
    skills_ml: str = Form(""),
    skills_tools: str = Form(""),
    experience_block: str = Form(""),
    projects_block: str = Form(""),
    education_lines: str = Form(""),
    publication_lines: str = Form(""),
):
    try:
        patch = {
            "basics": {
                "name": name.strip(),
                "email": email.strip(),
                "phone": phone.strip(),
                "linkedin": linkedin.strip(),
                "location": location.strip(),
                "open_to_relocation": (str(open_to_relocation).strip().lower() == "true"),
            },
            "summary": summary.strip(),
            "skills": {
                "Programming": parse_skill_csv(skills_programming),
                "Web & Frontend": parse_skill_csv(skills_web),
                "Data & Databases": parse_skill_csv(skills_data),
                "Data Analysis & ML": parse_skill_csv(skills_ml),
                "Tools": parse_skill_csv(skills_tools),
            },
            "experience": parse_experience_block(experience_block),
            "projects": parse_projects_block(projects_block),
            "education": parse_education_lines(education_lines),
            "publications": parse_publication_lines(publication_lines),
        }
        merge_save_profile(patch)
        return RedirectResponse(url="/settings/profile?saved=1", status_code=303)
    except Exception as e:
        msg = str(e).replace("\n", " ")
        return RedirectResponse(url=f"/settings/profile?error={quote(msg)}", status_code=303)

@app.get("/settings/output", response_class=HTMLResponse)
def settings_output(request: Request, saved: int = 0, error: str = ""):
    s = load_settings()
    ctx = {
        "request": request,
        "title": "Output Defaults",
        "tab": "output",
        "saved": bool(saved),
        "error": error,
        "settings": s,
        "p": load_profile(),
    }
    ctx.update(_common_context())
    return templates.TemplateResponse("settings_output.html", ctx)

@app.post("/settings/output/save")
def settings_output_save(
    default_role: str = Form("frontend"),
    resume_length: str = Form("1_page"),
    keyword_mode: str = Form("balanced"),
    summary_mode: str = Form("dynamic_with_override"),
):
    try:
        s = load_settings()
        s.setdefault("output", {})
        s["output"]["default_role"] = (default_role or "frontend").strip().lower()
        s["output"]["resume_length"] = (resume_length or "1_page").strip().lower()
        s["output"]["keyword_mode"] = (keyword_mode or "balanced").strip().lower()
        s["output"]["summary_mode"] = (summary_mode or "dynamic_with_override").strip().lower()
        save_settings(s)
        return RedirectResponse(url="/settings/output?saved=1", status_code=303)
    except Exception as e:
        msg = str(e).replace("\n", " ")
        return RedirectResponse(url=f"/settings/output?error={quote(msg)}", status_code=303)

@app.get("/settings/learning", response_class=HTMLResponse)
def settings_learning(request: Request, saved: int = 0, error: str = ""):
    s = load_settings()
    ctx = {
        "request": request,
        "title": "Learning",
        "tab": "learning",
        "saved": bool(saved),
        "error": error,
        "settings": s,
        "p": load_profile(),
    }
    ctx.update(_common_context())
    return templates.TemplateResponse("settings_learning.html", ctx)

@app.post("/settings/learning/save")
def settings_learning_save(
    enabled: str = Form("true"),
    learn_from_jds: str = Form("true"),
    confidence_threshold: float = Form(0.62),
):
    try:
        s = load_settings()
        s.setdefault("learning", {})
        s["learning"]["enabled"] = str(enabled).strip().lower() == "true"
        s["learning"]["learn_from_jds"] = str(learn_from_jds).strip().lower() == "true"
        ct = float(confidence_threshold)
        if ct < 0:
            ct = 0.0
        if ct > 1:
            ct = 1.0
        s["learning"]["confidence_threshold"] = ct
        save_settings(s)
        return RedirectResponse(url="/settings/learning?saved=1", status_code=303)
    except Exception as e:
        msg = str(e).replace("\n", " ")
        return RedirectResponse(url=f"/settings/learning?error={quote(msg)}", status_code=303)

@app.get("/settings/workflow", response_class=HTMLResponse)
def settings_workflow(request: Request, saved: int = 0, error: str = ""):
    s = load_settings()
    ctx = {
        "request": request,
        "title": "Workflow",
        "tab": "workflow",
        "saved": bool(saved),
        "error": error,
        "settings": s,
        "p": load_profile(),
    }
    ctx.update(_common_context())
    return templates.TemplateResponse("settings_workflow.html", ctx)

@app.post("/settings/workflow/save")
def settings_workflow_save(
    daily: int = Form(3),
    weekly: int = Form(15),
):
    try:
        s = load_settings()
        s.setdefault("targets", {})
        s["targets"]["daily"] = int(max(daily, 0))
        s["targets"]["weekly"] = int(max(weekly, 0))
        save_settings(s)
        return RedirectResponse(url="/settings/workflow?saved=1", status_code=303)
    except Exception as e:
        msg = str(e).replace("\n", " ")
        return RedirectResponse(url=f"/settings/workflow?error={quote(msg)}", status_code=303)
