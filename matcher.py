# matcher.py
from __future__ import annotations
import re
from typing import Dict, List, Tuple
from learning_store import load_store, get_concepts_for_role

def _norm(s: str) -> str:
    t = (s or "").strip().lower()
    t = t.replace("•", " ").replace("·", " ").replace("—", "-").replace("–", "-")
    t = re.sub(r"\s+", " ", t).strip()
    return t

def _token_set(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9\+#\.]+", _norm(s)))

def _partial_ratio(a: str, b: str) -> float:
    """
    Lightweight fuzzy match without extra deps.
    Good enough for: "state management" vs "redux toolkit" (concept layer will handle),
    and "testing" vs "test automation" etc.
    """
    A, B = _token_set(a), _token_set(b)
    if not A or not B:
        return 0.0
    inter = len(A & B)
    union = len(A | B)
    return inter / max(1, union)

def build_concept_index(role_family: str) -> Dict[str, List[str]]:
    store = load_store()
    return get_concepts_for_role(role_family, store)

def concept_match(jd_term: str, profile_terms: List[str], concept_index: Dict[str, List[str]]) -> Tuple[bool, str]:
    """
    If JD asks for a concept (e.g., "state management") and profile has any member term (redux/zustand),
    treat as matched with explanation.
    """
    jt = _norm(jd_term)
    if jt in concept_index:
        members = {_norm(x) for x in (concept_index.get(jt) or [])}
        prof = {_norm(x) for x in profile_terms}
        hit = members & prof
        if hit:
            top = sorted(hit)[0]
            return True, f"{jd_term} ↔ {top}"
    return False, ""

def match_terms(
    jd_terms: List[str],
    profile_terms: List[str],
    role_family: str,
    partial_threshold: float = 0.35,
) -> dict:
    """
    Returns:
      matched: exact/profile match
      partial: fuzzy partial matches
      concept: concept matches (JD concept satisfied by member skill)
      missing: what remains
    """
    jd = [_norm(x) for x in (jd_terms or []) if _norm(x)]
    prof_raw = [x for x in (profile_terms or []) if _norm(x)]
    prof = [_norm(x) for x in prof_raw]

    prof_set = set(prof)
    concept_index = build_concept_index(role_family)

    matched = []
    concept_hits = []
    partial = []  # (jd_term, best_profile_term, score)

    for jt_raw, jt in zip(jd_terms, jd):
        if jt in prof_set:
            matched.append(jt_raw)
            continue

        # concept match: "state management" satisfied by redux/zustand/mobx
        ok, expl = concept_match(jt_raw, prof_raw, concept_index)
        if ok:
            concept_hits.append(expl)
            continue

        # partial match fallback
        best = ("", 0.0)
        for p_raw, p in zip(prof_raw, prof):
            sc = _partial_ratio(jt, p)
            if sc > best[1]:
                best = (p_raw, sc)
        if best[1] >= partial_threshold:
            partial.append((jt_raw, best[0], round(best[1], 2)))

    # missing = jd terms not covered by any match type
    covered_norm = set(_norm(x) for x in matched)
    # for concept matches, treat the jd term as covered if it appears in explanation left side
    for expl in concept_hits:
        left = expl.split("↔")[0].strip()
        covered_norm.add(_norm(left))
    for jt, _, _ in partial:
        covered_norm.add(_norm(jt))

    missing = [x for x in jd_terms if _norm(x) and _norm(x) not in covered_norm]

    return {
        "matched": matched,
        "concept": concept_hits,
        "partial": partial,
        "missing": missing,
    }
