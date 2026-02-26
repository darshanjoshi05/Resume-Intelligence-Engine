import os, json
from typing import Dict, Any, List
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ✅ PUT YOUR “PRE-TRAIN LINES” HERE (few-shot examples).
# Each item: {"jd": "...", "out": {JSON that matches schema}}
FEW_SHOTS: List[Dict[str, Any]] = [
    # Example starter (replace with yours)
    # {"jd": "Company: X... Remote ...", "out": {"company":"X", "role_title":"...", ...}}
]

JD_SCHEMA: Dict[str, Any] = {
    "name": "jd_extract",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "company": {"type": "string"},
            "role_title": {"type": "string"},
            "job_location": {"type": "string"},
            "work_mode": {"type": "string", "enum": ["REMOTE", "HYBRID", "ONSITE", "UNKNOWN"]},
            "relocation_required": {"type": "boolean"},
            "must_have_skills": {"type": "array", "items": {"type": "string"}},
            "nice_to_have_skills": {"type": "array", "items": {"type": "string"}},
            "tools_tech": {"type": "array", "items": {"type": "string"}},
            "keywords": {"type": "array", "items": {"type": "string"}},
            "summary": {"type": "string"},
        },
        "required": [
            "company","role_title","job_location","work_mode","relocation_required",
            "must_have_skills","nice_to_have_skills","tools_tech","keywords","summary"
        ],
    },
}

SYSTEM = """You are a job-description parser for a resume tailoring app.
Return ONLY valid JSON matching the provided schema (strict).
Rules:
- Never invent details. If unknown/missing, use "" or UNKNOWN.
- Extract job location if present (City/State/Country). If not present, "".
- work_mode: REMOTE / HYBRID / ONSITE / UNKNOWN based on JD text.
- must_have_skills: hard requirements; nice_to_have_skills: preferred.
- tools_tech: frameworks, DBs, libraries, cloud, platforms.
- keywords: ATS keywords present in JD (concise, not spam).
- summary: 1–2 lines of what the job is about.
"""

def extract_jd_structured(jd_text: str, model: str = "gpt-5-mini") -> Dict[str, Any]:
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY missing in .env")

    # few-shot examples (your “pre-train lines”)
    shot_msgs = []
    for s in FEW_SHOTS[:6]:
        shot_msgs.append({"role": "user", "content": s["jd"]})
        shot_msgs.append({"role": "assistant", "content": json.dumps(s["out"], ensure_ascii=False)})

    resp = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": SYSTEM},
            *shot_msgs,
            {"role": "user", "content": jd_text[:20000]},
        ],
        text={"format": {"type": "json_schema", "json_schema": JD_SCHEMA, "strict": True}},
    )

    out = json.loads(resp.output_text)

    # normalize safety
    wm = out.get("work_mode", "UNKNOWN")
    if wm not in ("REMOTE","HYBRID","ONSITE","UNKNOWN"):
        out["work_mode"] = "UNKNOWN"

    # trim lists
    for k, cap in [("must_have_skills", 30), ("nice_to_have_skills", 30), ("tools_tech", 30), ("keywords", 60)]:
        out[k] = list(out.get(k, []))[:cap]

    return out
