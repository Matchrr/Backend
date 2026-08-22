from pydantic import BaseModel


class NetworkingEvent(BaseModel):
    id: str
    name: str
    location: str | None = None
    format: str = "in-person"
    starts_at: str | None = None
    url: str | None = None
    why_this_event: str | None = None
    match_percent: int | None = None
