from fastapi import APIRouter, HTTPException

from app.schemas.outreach import (
    OutreachDraft,
    OutreachDraftRequest,
    OutreachSendRequest,
    OutreachThread,
)
from app.services.outreach import build_draft
from app.services.store import store

router = APIRouter(prefix="/outreach", tags=["outreach"])


@router.post("/draft", response_model=OutreachDraft)
def draft_outreach(payload: OutreachDraftRequest) -> OutreachDraft:
    if not store.candidate.grounded:
        raise HTTPException(
            status_code=409,
            detail="Ground your profile first — outreach drafts cite verified facts only.",
        )

    job = store.get_job(payload.job_id) if payload.job_id else None
    if payload.job_id and job is None:
        raise HTTPException(status_code=404, detail=f"Unknown job {payload.job_id}")

    return build_draft(
        store.candidate,
        job,
        payload.recipient_email,
        payload.recipient_name,
        payload.extra_context,
    )


@router.post("/send", response_model=OutreachThread)
def send_outreach(payload: OutreachSendRequest) -> OutreachThread:
    if not payload.approved:
        raise HTTPException(
            status_code=403,
            detail="Nothing sends without explicit approval.",
        )
    return store.record_outreach(
        payload.recipient_email, payload.subject, payload.body, payload.job_id
    )


@router.get("/threads", response_model=list[OutreachThread])
def list_threads() -> list[OutreachThread]:
    return store.threads()
