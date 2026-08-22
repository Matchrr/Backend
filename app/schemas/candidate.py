from pydantic import BaseModel, Field


class CandidateCreate(BaseModel):
    target_title: str | None = None
    location: str | None = None
    linkedin_connected: bool = False


class Experience(BaseModel):
    title: str
    company: str
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None


class Candidate(BaseModel):
    id: str
    headline: str | None = None
    summary: str | None = None
    target_title: str | None = None
    location: str | None = None
    skills: list[str] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    linkedin_connected: bool = False
    gmail_connected: bool = False
