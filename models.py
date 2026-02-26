from pydantic import BaseModel

class GenerateRequest(BaseModel):
    company: str
    role_title: str
    jd_text: str
    role_override: str | None = None  # if user chooses
