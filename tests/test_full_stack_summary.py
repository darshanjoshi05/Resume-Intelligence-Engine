# tests/test_fullstack_summary.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

import copy
from resume_intel import apply_intelligence


FULLSTACK_JD = """
We’re looking for a performance-driven Full-Stack Developer to build modern web apps.
Responsibilities:
- Build rich UIs using React/Next.js
- Build APIs using Node.js
- Integrate REST/GraphQL APIs
- Write tests with Jest/Cypress
- Work with SQL/PostgreSQL
Skills: JavaScript/TypeScript, React, Next.js, Node.js, REST, GraphQL, Jest, Cypress, PostgreSQL
"""

def test_fullstack_assist_keeps_existing_summary():
    master = {
        "summary": "Existing summary should remain unchanged.",
        "skills": {"Core": ["React", "Node.js", "TypeScript", "PostgreSQL"]},
        "projects": [],
        "experience": [],
    }
    out = apply_intelligence(copy.deepcopy(master), role_family="Full Stack Developer", jd_text=FULLSTACK_JD, summary_mode="assist")
    assert out["summary"] == "Existing summary should remain unchanged."

def test_fullstack_assist_generates_when_empty():
    master = {
        "summary": "",
        "skills": {"Core": ["React", "Node.js", "TypeScript", "PostgreSQL", "Jest"]},
        "projects": [],
        "experience": [],
    }
    out = apply_intelligence(copy.deepcopy(master), role_family="Full Stack Developer", jd_text=FULLSTACK_JD, summary_mode="assist")
    assert out["summary"].strip() != ""
    assert ("full-stack" in out["summary"].lower()) or ("full stack" in out["summary"].lower())

def test_fullstack_auto_overwrites_existing_summary():
    master = {
        "summary": "Old summary should be replaced.",
        "skills": {"Core": ["React", "Node.js", "TypeScript", "PostgreSQL"]},
        "projects": [],
        "experience": [],
    }

    out = apply_intelligence(
        copy.deepcopy(master),
        role_family="Full Stack Developer",
        jd_text=FULLSTACK_JD,
        summary_mode="auto"
    )

    assert out["summary"] != "Old summary should be replaced."
    assert len(out["summary"]) > 0

def test_tech_blob_filters_noise_terms():
    master = {
        "summary": "",
        "skills": {
            "Core": [
                "React",
                "Node.js",
                "TypeScript",
                "Banana",
                "Communication",
                "Teamwork",
                "PostgreSQL",
                "Jest"
            ]
        },
        "projects": [],
        "experience": [],
    }

    out = apply_intelligence(
        copy.deepcopy(master),
        role_family="Full Stack Developer",
        jd_text=FULLSTACK_JD,
        summary_mode="auto"
    )

    summary = out["summary"].lower()

    assert "banana" not in summary
    assert "communication" not in summary
    assert "teamwork" not in summary

def test_project_selection_prefers_relevant_project():
    master = {
        "summary": "",
        "skills": {"Core": ["React", "Node.js", "TypeScript"]},
        "projects": [
            {
                "name": "E-commerce UI",
                "tech": "React, TailwindCSS",
                "bullets": [
                    "Built responsive frontend UI",
                    "Integrated REST APIs"
                ]
            },
            {
                "name": "Data Pipeline",
                "tech": "Python, Pandas",
                "bullets": [
                    "Built ETL pipeline",
                    "Processed CSV data"
                ]
            }
        ],
        "experience": [],
    }

    out = apply_intelligence(
        copy.deepcopy(master),
        role_family="Full Stack Developer",
        jd_text=FULLSTACK_JD,
        summary_mode="assist"
    )

    selected_projects = out.get("projects", [])

    assert len(selected_projects) > 0
    assert "E-commerce" in selected_projects[0]["name"]
def test_summary_not_keyword_dump():
    master = {
        "summary": "",
        "skills": {"Core": ["React", "Next.js", "Node.js", "TypeScript", "PostgreSQL", "Jest", "Cypress", "GraphQL", "REST"]},
        "projects": [],
        "experience": [],
    }

    out = apply_intelligence(
        copy.deepcopy(master),
        role_family="Full Stack Developer",
        jd_text=FULLSTACK_JD,
        summary_mode="auto"
    )

    s = out["summary"]
    # must have at least 2 sentences (not just "Core strengths: X, Y, Z")
    assert s.count(".") >= 2

    # cap tech terms: avoid dumping 12+ comma-separated items into one line
    assert s.count(",") <= 10

def test_skill_reordering_prioritizes_jd_terms():
    master = {
        "summary": "",
        "skills": {
            "Frontend": ["React", "Next.js", "CSS"],
            "Backend": ["Node.js", "Express"],
            "Data": ["Python", "Pandas"]
        },
        "projects": [],
        "experience": [],
    }

    react_heavy_jd = "Looking for a React developer with strong React and Next.js experience."

    out = apply_intelligence(
        copy.deepcopy(master),
        role_family="Full Stack Developer",
        jd_text=react_heavy_jd,
        summary_mode="assist"
    )

    skills = out["skills"]
    first_category = list(skills.keys())[0]

    assert first_category == "Frontend"

def test_skill_items_reorder_within_category():
    master = {
        "summary": "",
        "skills": {
            "Frontend": ["React", "Next.js", "CSS"]
        },
        "projects": [],
        "experience": [],
    }

    nextjs_heavy_jd = "Seeking engineer with strong Next.js experience and Next.js optimization skills."

    out = apply_intelligence(
        copy.deepcopy(master),
        role_family="Full Stack Developer",
        jd_text=nextjs_heavy_jd,
        summary_mode="assist"
    )

    skills = out["skills"]
    frontend_items = skills["Frontend"]

    assert frontend_items[0] == "Next.js"

def test_alignment_score_computes_coverage():
    master = {
        "summary": "",
        "skills": {"Core": ["React", "Node.js", "TypeScript"]},
        "projects": [],
        "experience": [],
    }

    jd = "Looking for React and Node.js developer with GraphQL experience."

    out = apply_intelligence(
        copy.deepcopy(master),
        role_family="Full Stack Developer",
        jd_text=jd,
        summary_mode="assist"
    )

    alignment = out["_alignment"]

    assert alignment["coverage_percent"] > 0
    assert "graphql" in alignment["missing_terms"]
