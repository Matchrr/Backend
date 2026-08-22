from datetime import datetime

from pydantic import BaseModel


class Application(BaseModel):
    id: str
    candidate_id: str
    job_id: str
    status: str = "draft"
    created_at: datetime | None = None
