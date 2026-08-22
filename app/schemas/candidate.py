from pydantic import BaseModel, Field


class CandidateUpdate(BaseModel):
    target_title: str | None = None
    location: str | None = None
    headline: str | None = None
    summary: str | None = None


class CandidateCreate(BaseModel):
    target_title: str | None = None
    location: str | None = None
    linkedin_connected: bool = False


class Experience(BaseModel):
    title: str
    company: str
    start_date: str | None = None
    end_date: str | None = None
    bullets: list[str] = Field(default_factory=list)


class Candidate(BaseModel):
    """The Ground Truth Profile.

    Everything downstream (matching, growth, tailoring, outreach) may only cite
    facts present on this object.
    """

    id: str
    full_name: str | None = None
    headline: str | None = None
    summary: str | None = None
    target_title: str | None = None
    location: str | None = None
    skills: list[str] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    grounded: bool = False
    grounding_sources: list[str] = Field(default_factory=list)
    linkedin_connected: bool = False
    gmail_connected: bool = False

    @property
    def achievements(self) -> list[str]:
        return [bullet for role in self.experience for bullet in role.bullets]

    @property
    def profile_text(self) -> str:
        parts = [
            self.headline or "",
            self.summary or "",
            self.target_title or "",
            " ".join(self.skills),
        ]
        for role in self.experience:
            parts.append(f"{role.title} {role.company} {' '.join(role.bullets)}")
        parts.extend(self.education)
        parts.extend(self.certifications)
        return " ".join(part for part in parts if part)
