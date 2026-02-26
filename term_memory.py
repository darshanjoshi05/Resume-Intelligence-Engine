# term_memory.py
from __future__ import annotations
import json
import re
from pathlib import Path
from typing import Dict, Set, Tuple, List

DATA_PATH = Path("data") / "term_memory.json"

DEFAULT = {
    "verified": [],          # list[str]
    "ignored": [],           # list[str]
    "synonyms": {},          # dict[str,str]  e.g. "reactjs": "react"
}

HR_NOISE = {
    "benefits", "benefit", "insurance", "medical", "dental", "vision",
    "hsa", "fsa", "pto", "leave", "paid time off", "holiday", "holidays",
    "disability", "401k", "retirement", "wellness", "equal opportunity",
    "eeo", "accommodation", "background check", "drug test", "salary",
    "compensation", "bonus", "bonuses", "vaccination"
}

def _norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = s.replace("•", " ").replace("·", " ").replace("—", "-")
    s = re.sub(r"\s+", " ", s)
    s = s.strip(" .,:;|/\\")
    return s

def load_memory() -> dict:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not DATA_PATH.exists():
        DATA_PATH.write_text(json.dumps(DEFAULT, indent=2), encoding="utf-8")
        return dict(DEFAULT)

    try:
        obj = json.loads(DATA_PATH.read_text(encoding="utf-8"))
        if not isinstance(obj, dict):
            return dict(DEFAULT)
        for k in DEFAULT:
            obj.setdefault(k, DEFAULT[k])
        if not isinstance(obj.get("synonyms"), dict):
            obj["synonyms"] = {}
        if not isinstance(obj.get("verified"), list):
            obj["verified"] = []
        if not isinstance(obj.get("ignored"), list):
            obj["ignored"] = []
        return obj
    except Exception:
        return dict(DEFAULT)

def save_memory(mem: dict) -> None:
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATA_PATH.write_text(json.dumps(mem, indent=2, ensure_ascii=False), encoding="utf-8")

def apply_synonyms(term: str, mem: dict) -> str:
    t = _norm(term)
    syn = mem.get("synonyms", {}) or {}
    # allow chained: reactjs -> react
    for _ in range(3):
        nxt = syn.get(t)
        if not nxt:
            break
        t = _norm(nxt)
    return t

def is_noise(term: str) -> bool:
    t = _norm(term)
    if not t:
        return True
    if t in HR_NOISE:
        return True
    if "http://" in t or "https://" in t or "www." in t:
        return True
    if re.search(r"\b[a-z0-9\-]+\.(com|org|net|io|ai|edu)\b", t):
        return True
    if len(t) <= 2:
        return True
    # long benefit-like fragments
    if len(t) > 40 and " " in t:
        return True
    return False

def bucket_missing_terms(
    missing_terms: List[str],
    jd_must: List[str],
    jd_nice: List[str],
    mem: dict,
) -> dict:
    """
    Returns buckets:
      - must: terms that appear in JD must list
      - nice: terms that appear in JD nice list
      - other: remaining (but not noise)
      - hidden_noise: filtered noise (not shown)
      - verified_hits: terms user verified (not shown as missing)
      - ignored_hits: terms user ignored (not shown as missing)
    """
    verified = set(_norm(x) for x in (mem.get("verified") or []))
    ignored = set(_norm(x) for x in (mem.get("ignored") or []))

    must_set = set(_norm(x) for x in (jd_must or []))
    nice_set = set(_norm(x) for x in (jd_nice or []))

    out = {
        "must": [],
        "nice": [],
        "other": [],
        "hidden_noise": [],
        "verified_hits": [],
        "ignored_hits": [],
    }

    seen = set()
    for raw in (missing_terms or []):
        t = apply_synonyms(raw, mem)
        if not t or t in seen:
            continue
        seen.add(t)

        if is_noise(t):
            out["hidden_noise"].append(t)
            continue
        if t in ignored:
            out["ignored_hits"].append(t)
            continue
        if t in verified:
            out["verified_hits"].append(t)
            continue

        if t in must_set:
            out["must"].append(t)
        elif t in nice_set:
            out["nice"].append(t)
        else:
            out["other"].append(t)

    return out

def add_verified(term: str) -> None:
    mem = load_memory()
    t = _norm(term)
    if not t:
        return
    if t not in set(_norm(x) for x in mem.get("verified", [])):
        mem["verified"].append(t)
    save_memory(mem)

def add_ignored(term: str) -> None:
    mem = load_memory()
    t = _norm(term)
    if not t:
        return
    if t not in set(_norm(x) for x in mem.get("ignored", [])):
        mem["ignored"].append(t)
    save_memory(mem)

def add_synonym(src: str, dst: str) -> None:
    mem = load_memory()
    s = _norm(src)
    d = _norm(dst)
    if not s or not d or s == d:
        return
    mem.setdefault("synonyms", {})
    mem["synonyms"][s] = d
    save_memory(mem)
