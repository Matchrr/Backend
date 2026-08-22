from fastapi import APIRouter, HTTPException, Query

from app.schemas.job import Job
from app.services.store import store

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/matches", response_model=list[Job])
def list_job_matches(limit: int = Query(10, ge=1, le=50)) -> list[Job]:
    return store.job_matches(limit=limit)


@router.post("/sync")
def sync_jobs() -> dict[str, object]:
    return store.sync_jobs()


@router.get("/{job_id}", response_model=Job)
def get_job(job_id: str) -> Job:
    job = store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Unknown job {job_id}")
    return job
