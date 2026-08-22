"""Dashboard aggregate.

The overview endpoint is the landing surface's single read. Everything the
dashboard renders is derived server-side so the client does not have to fan out
across five endpoints and re-derive the same numbers.
"""

from pydantic import BaseModel, Field


class ActivityEntry(BaseModel):
    id: str
    kind: str
    title: str
    detail: str | None = None
    tone: str = "neutral"
    at: str


class PipelineStage(BaseModel):
    """One step of the funnel from scored corpus down to sent outreach."""

    key: str
    label: str
    count: int
    percent: float
    tone: str
    hint: str | None = None


class MatchPoint(BaseModel):
    """A single ranked role, shaped for the fit-curve chart."""

    label: str
    title: str
    company: str
    match: int
    coverage: int


class ScoreBand(BaseModel):
    label: str
    count: int
    tone: str


class NextAction(BaseModel):
    label: str
    description: str
    href: str
    cta: str


class Overview(BaseModel):
    grounded: bool
    grounding_sources: list[str] = Field(default_factory=list)
    target_title: str | None = None
    candidate_name: str | None = None
    location: str | None = None

    skill_count: int = 0
    jobs_in_corpus: int = 0
    top_match_percent: int | None = None
    average_match_percent: int | None = None
    strong_matches: int = 0
    targeted_count: int = 0
    target_limit: int = 5
    dossiers_ready: int = 0
    events_matched: int = 0
    events_saved: int = 0
    outreach_sent: int = 0
    outreach_goal: int = 5
    recruiters_emailed: int = 0
    open_skill_gaps: int = 0
    profile_completeness: int = 0
    last_sync: str | None = None

    linkedin_connected: bool = False
    gmail_connected: bool = False

    pipeline: list[PipelineStage] = Field(default_factory=list)
    match_curve: list[MatchPoint] = Field(default_factory=list)
    score_bands: list[ScoreBand] = Field(default_factory=list)
    activity: list[ActivityEntry] = Field(default_factory=list)
    next_action: NextAction | None = None
