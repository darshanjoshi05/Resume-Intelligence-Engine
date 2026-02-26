def pick_template(jd_text: str, role_family: str) -> str:
    t = jd_text.lower()

    # Rules first (fast + robust)
    if role_family in ("DATA_ANALYST",):
        return "data_modern"
    if role_family in ("JAVA_FULLSTACK", "FULLSTACK_GENERAL"):
        return "fullstack_modern"
    if role_family in ("REACT_FRONTEND",):
        return "frontend_modern"

    # If JD screams "years of experience" prioritize experience
    if "years" in t or "experience" in t:
        return "experience_heavy"

    # If JD mentions research/ML
    if "machine learning" in t or "research" in t or "publication" in t:
        return "project_heavy"

    return "classic"
