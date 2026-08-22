from pydantic import BaseModel, Field


class NetworkingEvent(BaseModel):
    id: str
    name: str
    organizer: str | None = None
    location: str | None = None
    format: str = "in-person"
    starts_at: str | None = None
    url: str | None = None
    description: str | None = None
    attendee_profile: str | None = None
    topics: list[str] = Field(default_factory=list)
    why_this_event: str | None = None
    match_percent: int | None = None
    saved: bool = False
