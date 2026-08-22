from pydantic import BaseModel


class Application(BaseModel):
    id: str
    candidate_id: str
    job_id: str
    job_title: str | None = None
    company: str | None = None
    status: str = "targeted"
    created_at: str | None = None
