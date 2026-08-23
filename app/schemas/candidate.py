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
    location: str | None = None
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
    email: str | None = None
    picture_url: str | None = None
    websites: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    volunteering: list[Experience] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    honors: list[str] = Field(default_factory=list)
    grounded: bool = False
    grounding_sources: list[str] = Field(default_factory=list)
    linkedin_connected: bool = False
    linkedin_member_id: str | None = None
    linkedin_coverage: str = "none"
    gmail_connected: bool = False

    @property
    def achievements(self) -> list[str]:
        volunteer_bullets = [bullet for role in self.volunteering for bullet in role.bullets]
        return [bullet for role in self.experience for bullet in role.bullets] + volunteer_bullets

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
        for role in self.volunteering:
            parts.append(f"{role.title} {role.company} {' '.join(role.bullets)}")
        parts.extend(self.education)
        parts.extend(self.certifications)
        parts.extend(self.projects)
        parts.extend(self.languages)
        parts.extend(self.honors)
        return " ".join(part for part in parts if part)
