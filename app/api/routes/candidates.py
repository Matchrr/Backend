from fastapi import APIRouter, File, HTTPException, UploadFile

from app.data.seed import DEMO_LINKEDIN_PROFILE
from app.schemas.candidate import Candidate, CandidateUpdate
from app.services.grounding import (
    extract_pdf_text,
    ground_from_linkedin,
    ground_from_resume,
    merge_profiles,
)
from app.services.store import store

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.get("/me", response_model=Candidate)
def get_current_candidate() -> Candidate:
    return store.candidate


@router.patch("/me", response_model=Candidate)
def update_current_candidate(payload: CandidateUpdate) -> Candidate:
    return store.update_candidate(**payload.model_dump(exclude_unset=True))


@router.post("/linkedin", response_model=Candidate)
def ground_with_linkedin() -> Candidate:
    """Stands in for the LinkedIn OAuth callback until the connector lands."""
    incoming = ground_from_linkedin(DEMO_LINKEDIN_PROFILE, store.candidate.target_title)
    if store.candidate.grounded:
        return store.set_candidate(merge_profiles(store.candidate, incoming))
    return store.set_candidate(incoming)


@router.post("/resume", response_model=Candidate)
async def upload_resume(file: UploadFile = File(...)) -> Candidate:
    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    text = extract_pdf_text(payload)
    if not text.strip():
        raise HTTPException(
            status_code=422,
            detail=(
                "Could not extract text from that file. Scanned or image-only PDFs need OCR, "
                "which is not wired up yet."
            ),
        )

    incoming = ground_from_resume(text, store.candidate.target_title)
    if not incoming.skills and not incoming.experience:
        raise HTTPException(
            status_code=422,
            detail="Extracted text, but found no recognizable skills or work history.",
        )

    if store.candidate.grounded:
        return store.set_candidate(merge_profiles(store.candidate, incoming))
    return store.set_candidate(incoming)


@router.post("/reset", response_model=Candidate)
def reset_candidate() -> Candidate:
    store.reset()
    return store.candidate
