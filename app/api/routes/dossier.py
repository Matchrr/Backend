from fastapi import APIRouter, HTTPException

from app.schemas.dossier import Dossier
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
        return store.generate_dossier(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown job {job_id}") from None


@router.get("/{job_id}", response_model=Dossier)
def get_dossier(job_id: str) -> Dossier:
    existing = store.get_dossier(job_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="No dossier generated for this job yet.")
    return existing
