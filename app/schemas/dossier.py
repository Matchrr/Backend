from pydantic import BaseModel, Field


class TailoredBullet(BaseModel):
    original: str
    tailored: str
    emphasized_skills: list[str] = Field(default_factory=list)
    changed: bool = False


class AtsAnswer(BaseModel):
    question: str
    answer: str


class GroundingCheck(BaseModel):
    """Result of verifying that nothing in the dossier was invented."""

    passed: bool
    claims_checked: int
    rejected_claims: list[str] = Field(default_factory=list)
    note: str


class Dossier(BaseModel):
    job_id: str
    job_title: str
    company: str
    summary: str
    tailored_bullets: list[TailoredBullet] = Field(default_factory=list)
    cover_letter: str
    ats_answers: list[AtsAnswer] = Field(default_factory=list)
    grounding: GroundingCheck
    generated_at: str
