from pydantic import BaseModel, Field


class OutreachDraftRequest(BaseModel):
    recipient_email: str = Field(..., min_length=3)
    recipient_name: str | None = None
    job_id: str | None = None
    extra_context: str | None = None


class OutreachDraft(BaseModel):
    subject: str
    body: str
    recipient_email: str
    recipient_name: str | None = None
    job_id: str | None = None
    grounded_facts: list[str] = Field(default_factory=list)


class OutreachSendRequest(BaseModel):
    subject: str
    body: str
    recipient_email: str = Field(..., min_length=3)
    job_id: str | None = None
    approved: bool = False


class OutreachThread(BaseModel):
    id: str
    recipient_email: str
    subject: str
    body: str
    job_id: str | None = None
    job_title: str | None = None
    status: str = "sent"
    sent_at: str
