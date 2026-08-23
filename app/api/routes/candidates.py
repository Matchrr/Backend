from fastapi import APIRouter, File, HTTPException, UploadFile

from app.data.seed import DEMO_LINKEDIN_PROFILE
from app.schemas.candidate import Candidate, CandidateUpdate
from app.services.career_parse import city_only_location
from app.services.grounding import (
    extract_pdf_text,
    ground_from_extracted,
    ground_from_linkedin,
    ground_from_resume,
    merge_profiles,
    overlay_document,
)
from app.services import nutrient as nutrient_service
from app.services.store import store

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.get("/me", response_model=Candidate)
def get_current_candidate() -> Candidate:
    current = store.candidate
    if current.location:
        cleaned = city_only_location(current.location)
        if cleaned and cleaned != current.location:
            current.location = cleaned
    return current


@router.patch("/me", response_model=Candidate)
def update_current_candidate(payload: CandidateUpdate) -> Candidate:
    return store.update_candidate(**payload.model_dump(exclude_unset=True))


@router.post("/linkedin", response_model=Candidate)
def ground_with_linkedin() -> Candidate:
    """Demo import when LinkedIn OAuth credentials are not configured.

    The real Sign in with LinkedIn flow lives at GET /api/integrations/linkedin/authorize.
    """
    incoming = ground_from_linkedin(DEMO_LINKEDIN_PROFILE, store.candidate.target_title)
    if store.candidate.grounded:
        return store.set_candidate(merge_profiles(store.candidate, incoming))
    return store.set_candidate(incoming)


@router.post("/resume", response_model=Candidate)
async def upload_resume(file: UploadFile = File(...)) -> Candidate:
    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    filename = file.filename or "resume.pdf"
    incoming = _ingest_document(payload, filename)
    if not incoming.skills and not incoming.experience:
        raise HTTPException(
            status_code=422,
            detail="Extracted text, but found no recognizable skills or work history.",
        )

    if store.candidate.grounded or store.candidate.linkedin_connected:
        return store.set_candidate(overlay_document(store.candidate, incoming))
    return store.set_candidate(incoming)


def _ingest_document(payload: bytes, filename: str) -> Candidate:
    """Nutrient first (OCR + schema extract), local parser as fallback."""
    target = store.candidate.target_title
    is_pdf = payload[:5] == b"%PDF-"

    if is_pdf and nutrient_service.is_configured():
        try:
            text, structured = nutrient_service.ingest_pdf(payload, filename)
        except nutrient_service.NutrientError as exc:
            text, structured = extract_pdf_text(payload), None
            if not text.strip():
                raise HTTPException(status_code=422, detail=str(exc)) from exc
        extracted = (
            ground_from_extracted(structured, target, source="resume") if structured else None
        )
        parsed = ground_from_resume(text, target) if text.strip() else None
        if extracted and extracted.grounded:
            if parsed:
                extracted.full_name = extracted.full_name or parsed.full_name
                extracted.headline = extracted.headline or parsed.headline
                extracted.location = extracted.location or parsed.location
                extracted.email = extracted.email or parsed.email
                if not extracted.summary:
                    extracted.summary = parsed.summary
                if not extracted.experience and parsed.experience:
                    extracted.experience = parsed.experience
                if not extracted.education and parsed.education:
                    extracted.education = parsed.education
            return extracted
        if parsed and (parsed.skills or parsed.experience or parsed.education):
            return parsed
        raise HTTPException(
            status_code=422,
            detail="Nutrient read the PDF, but found no recognizable skills or work history.",
        )

    text = extract_pdf_text(payload)
    if not text.strip():
        raise HTTPException(
            status_code=422,
            detail=(
                "Could not extract text from that file. Add NUTRIENT_API_KEY for OCR, "
                "or upload a text-based PDF."
            ),
        )
    return ground_from_resume(text, target)


@router.post("/reset", response_model=Candidate)
def reset_candidate() -> Candidate:
    store.reset()
    return store.candidate
