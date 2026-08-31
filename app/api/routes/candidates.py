from __future__ import annotations

import hashlib
import logging

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.data.seed import DEMO_LINKEDIN_PROFILE
from app.schemas.candidate import Candidate, CandidateUpdate
from app.services import nutrient as nutrient_service
from app.services import s3_store, xano_profile
from app.services.ai_client import parse_xano_user_id
from app.services.career_parse import city_only_location
from app.services.grounding import (
    extract_pdf_text,
    ground_from_extracted,
    ground_from_linkedin,
    ground_from_resume,
    merge_profiles,
    overlay_document,
)
from app.services.profile_index import commit_grounded
from app.services.profile_vault import is_persisted_user
from app.services.store import store

router = APIRouter(prefix="/candidates", tags=["candidates"])
logger = logging.getLogger(__name__)
MAX_UPLOAD_BYTES = s3_store.MAX_SOURCE_BYTES


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
        return commit_grounded(merge_profiles(store.candidate, incoming))
    return commit_grounded(incoming)


@router.post("/resume", response_model=Candidate)
async def upload_resume(
    file: UploadFile = File(...),
    kind: str = Form("resume"),
) -> Candidate:
    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(payload) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File exceeds the 10 MB upload cap.")

    source_kind = _normalize_kind(kind)
    filename = file.filename or "resume.pdf"
    is_pdf = payload[:5] == b"%PDF-"
    if source_kind == "linkedin_pdf" and not is_pdf:
        raise HTTPException(status_code=400, detail="LinkedIn Save-to-PDF must be a PDF.")

    preview = ""
    if is_pdf:
        try:
            preview = extract_pdf_text(payload)[:2000]
        except Exception:
            preview = ""
    else:
        preview = payload[:2000].decode("utf-8", "ignore")
    _store_source_pdf(
        payload,
        filename=filename,
        content_type=file.content_type or "",
        kind=source_kind,
        nutrient_ok=is_pdf and nutrient_service.is_configured(),
        preview=preview,
    )

    incoming = _ingest_document(payload, filename, source=source_kind)
    if not incoming.skills and not incoming.experience:
        raise HTTPException(
            status_code=422,
            detail="Extracted text, but found no recognizable skills or work history.",
        )

    if store.candidate.grounded or store.candidate.linkedin_connected:
        return commit_grounded(overlay_document(store.candidate, incoming))
    return commit_grounded(incoming)


def _ingest_document(payload: bytes, filename: str, source: str = "resume") -> Candidate:
    """Nutrient first (OCR + schema extract), local parser as fallback."""
    target = store.candidate.target_title
    is_pdf = payload[:5] == b"%PDF-"
    grounding_source = "linkedin_pdf" if source == "linkedin_pdf" else "resume"

    if is_pdf and nutrient_service.is_configured():
        try:
            text, structured = nutrient_service.ingest_pdf(payload, filename)
        except nutrient_service.NutrientError as exc:
            text, structured = extract_pdf_text(payload), None
            if not text.strip():
                raise HTTPException(status_code=422, detail=str(exc)) from exc
        extracted = (
            ground_from_extracted(structured, target, source=grounding_source) if structured else None
        )
        parsed = ground_from_resume(text, target) if text.strip() else None
        if parsed and grounding_source != "resume":
            parsed.grounding_sources = [grounding_source] if parsed.grounded else []
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
    parsed = ground_from_resume(text, target)
    if grounding_source != "resume" and parsed.grounded:
        parsed.grounding_sources = [grounding_source]
    return parsed


def _normalize_kind(kind: str) -> str:
    raw = (kind or "resume").strip().lower().replace("-", "_")
    if raw in {"linkedin_pdf", "linkedin"}:
        return "linkedin_pdf"
    return "resume"


def _store_source_pdf(
    payload: bytes,
    *,
    filename: str,
    content_type: str,
    kind: str,
    nutrient_ok: bool,
    preview: str,
) -> None:
    if payload[:5] != b"%PDF-":
        return
    if not s3_store.configured():
        return
    user_id = parse_xano_user_id(store.candidate.id)
    if user_id is None or not is_persisted_user(store.candidate.id):
        return
    digest = hashlib.sha256(payload).hexdigest()
    try:
        key = s3_store.put_source_pdf(user_id=user_id, sha256=digest, body=payload, kind=kind)
    except s3_store.S3StoreError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    try:
        xano_profile.record_source_document(
            user_id=user_id,
            kind=kind,
            original_filename=filename,
            content_type=content_type or "application/pdf",
            byte_size=len(payload),
            sha256=digest,
            s3_key=key,
            nutrient_ok=nutrient_ok,
            extracted_text_preview=preview,
        )
    except Exception:
        logger.exception("Could not record source document for user %s", user_id)


@router.post("/reset", response_model=Candidate)
def reset_candidate() -> Candidate:
    return store.reset_profile()
