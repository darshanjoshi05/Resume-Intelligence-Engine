import json

FRONTEND_JD = """
Frontend Developer. React, Next.js, Angular. TailwindCSS, Styled Components.
Redux Toolkit, Zustand, MobX. Lighthouse. WCAG 2.1. Jest, Cypress, Playwright.
Webpack, Vite, Rollup. Storybook, Figma.
"""

BACKEND_JD = """
Backend Developer. Java, Python. REST APIs. SQL/Postgres. MongoDB.
Auth (JWT/OAuth). Caching (Redis). Unit/integration testing. Performance tuning.
"""

FULLSTACK_JD = """
Full-stack Developer. React + TypeScript on frontend. Java/Python on backend.
REST APIs, SQL databases, testing, performance, and deployment.
"""

BAD_LEAK_TOKENS = [
    "aligned:", "(aligned:",
    "debug:", "debug_", "__debug__",
    "traceback", "exception", "keyerror",
    "nonetype", "todo_", "fixme", "stack trace"
]

def stable_dump(x) -> str:
    return json.dumps(x, sort_keys=True, ensure_ascii=False)

def all_text(out: dict) -> str:
    parts = []
    parts.append(str(out.get("summary") or ""))

    skills = out.get("skills") or {}
    if isinstance(skills, dict):
        for _, items in skills.items():
            if isinstance(items, list):
                parts.extend([str(x) for x in items])
            else:
                parts.append(str(items))
    elif isinstance(skills, list):
        parts.extend([str(x) for x in skills])

    for p in (out.get("projects") or []):
        if isinstance(p, dict):
            parts.append(str(p.get("name", "")))
            parts.append(str(p.get("tech", "")))
            parts.extend([str(b) for b in (p.get("bullets") or [])])

    for e in (out.get("experience") or []):
        if isinstance(e, dict):
            parts.append(str(e.get("title", "")))
            parts.append(str(e.get("org", "")))
            parts.extend([str(b) for b in (e.get("bullets") or [])])

    return "\n".join(parts)

def first_skills_bucket_text(skills) -> str:
    if isinstance(skills, dict) and skills:
        first_key = next(iter(skills.keys()))
        v = skills.get(first_key)
        if isinstance(v, list):
            return " ".join(map(str, v))
        return str(v or "")
    if isinstance(skills, list):
        return " ".join(map(str, skills))
    return ""