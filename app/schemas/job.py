from pydantic import BaseModel, Field


class FitScorecard(BaseModel):
    match_percent: int
    similarity: float = 0.0
    matching_skills: list[str] = Field(default_factory=list)
    missing_tech: list[str] = Field(default_factory=list)
    key_angle: str | None = None


class Job(BaseModel):
    id: str
    title: str
    company: str
    location: str | None = None
    source: str | None = None
    posted_at: str | None = None
    salary: str | None = None
    apply_url: str | None = None
    description: str | None = None
    scorecard: FitScorecard | None = None
    targeted: bool = False
