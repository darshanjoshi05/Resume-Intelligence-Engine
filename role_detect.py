import re

ROLE_FAMILIES = [
    "JAVA_FULLSTACK",
    "SOFTWARE_ENGINEER",
    "APPLICATION_DEVELOPER",
    "DATA_ANALYST",
    "REACT_FRONTEND",
    "FULLSTACK_GENERAL",
]

def detect_role_family(jd: str) -> str:
    t = (jd or "").lower()

    data_hits = sum(kw in t for kw in [
        "pandas", "numpy", "tableau", "power bi", "dashboard",
        "data analyst", "sql", "visualization", "etl", "data pipeline",
    ])

    java_hits = sum(kw in t for kw in [
        "java", "spring", "spring boot", "microservices", "hibernate", "jpa",
        "rest api", "backend", "service",
    ])

    react_hits = sum(kw in t for kw in [
        "react", "next.js", "nextjs", "angular", "frontend", "javascript", "typescript",
        "html", "css", "tailwind", "styled components", "css-in-js",
        "redux", "redux toolkit", "zustand", "mobx", "state management",
        "webpack", "vite", "rollup",
        "jest", "cypress", "playwright",
        "lighthouse", "code splitting", "lazy loading", "wcag", "accessibility",
    ])

    app_hits = sum(kw in t for kw in [
        "application developer", "application", "integration",
        "testing", "deployment", "requirements", "support",
    ])

    swe_hits = sum(kw in t for kw in [
        "software engineer", "algorithms", "data structures",
        "debugging", "design patterns", "system design",
    ])

    scores = {
        "DATA_ANALYST": data_hits,
        "JAVA_FULLSTACK": java_hits,
        "REACT_FRONTEND": react_hits,
        "APPLICATION_DEVELOPER": app_hits,
        "SOFTWARE_ENGINEER": swe_hits,
        "FULLSTACK_GENERAL": java_hits + react_hits,
    }

    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return "SOFTWARE_ENGINEER"
    return best
