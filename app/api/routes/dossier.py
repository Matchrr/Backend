from fastapi import APIRouter, HTTPException

from app.schemas.dossier import Dossier
from app.services import ai_client
from app.services.store import store

router = APIRouter(prefix="/dossier", tags=["dossier"])


@router.post("/{job_id}", response_model=Dossier)
def generate_dossier(job_id: str) -> Dossier:
    if not store.candidate.grounded:
        raise HTTPException(
            status_code=409,
            detail="Ground your profile before generating a dossier.",
        )
    try:
        built = store.generate_dossier(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown job {job_id}") from None
    rag = _try_rag_cover_letter(job_id)
    if rag:
        attached = store.attach_rag_cover_letter(job_id, rag)
        if attached is not None:
            return attached
    return built


@router.get("/{job_id}", response_model=Dossier)
def get_dossier(job_id: str) -> Dossier:
    existing = store.get_dossier(job_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="No dossier generated for this job yet.")
    return existing


def _try_rag_cover_letter(job_id: str) -> dict | None:
    if not ai_client.ai_service_reachable():
        return None
    job = store.get_job(job_id)
    if job is None:
        return None
    candidate = store.candidate
    scorecard = job.scorecard
    payload = {
        "candidate_id": candidate.id,
        "job_id": job.id,
        "user_id": ai_client.parse_xano_user_id(candidate.id),
        "xano_job_id": store.job_xano_id(job_id),
        "job_title": job.title,
        "company": job.company,
        "job_description": job.description or "",
        "matching_skills": list(scorecard.matching_skills) if scorecard else [],
        "missing_tech": list(scorecard.missing_tech) if scorecard else [],
        "key_angle": scorecard.key_angle if scorecard else None,
        "profile_revision_id": store.profile_revision_id(),
        "profile": store.profile_payload(),
    }
    try:
        result = ai_client.generate_cover_letter(payload)
    except Exception:
        return None
    if not isinstance(result, dict) or not result.get("cover_letter"):
        return None
    return result
