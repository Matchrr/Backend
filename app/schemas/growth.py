from pydantic import BaseModel, Field


class LearningResource(BaseModel):
    title: str
    kind: str
    url: str
    provider: str | None = None
    why: str | None = None


class SkillGap(BaseModel):
    skill: str
    priority: int = 1
    resources: list[LearningResource] = Field(default_factory=list)


class GrowthPlan(BaseModel):
    target_title: str | None = None
    skill_gaps: list[SkillGap] = Field(default_factory=list)
