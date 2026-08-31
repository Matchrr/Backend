from fastapi import APIRouter, Body, HTTPException, Query
from pydantic import BaseModel
import httpx

from app.schemas.job import Job
from app.services import ai_client
from app.services.store import store

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobSyncBody(BaseModel):
    work_modes: list[str] | None = None
    employment_types: list[str] | None = None
    pay_min: float | None = None
    pay_period: str | None = None


def _split_csv(value: str | None) -> list[str] | None:
    if not value:
        return None
    items = [part.strip() for part in value.split(",") if part.strip()]
    return items or None


@router.get("/matches", response_model=list[Job])
def list_job_matches(
    limit: int = Query(10, ge=1, le=50),
    work_modes: str | None = None,
    employment_types: str | None = None,
    pay_min: float | None = None,
    pay_period: str | None = None,
) -> list[Job]:
    candidate = store.candidate
    filters = {
        "work_modes": _split_csv(work_modes) or store.match_filters.get("work_modes"),
        "employment_types": _split_csv(employment_types)
        or store.match_filters.get("employment_types"),
        "pay_min": pay_min if pay_min is not None else store.match_filters.get("pay_min"),
        "pay_period": pay_period or store.match_filters.get("pay_period"),
    }
    if not ai_client.ai_service_reachable() or not candidate.grounded:
        return store.job_matches(limit=limit)
    try:
        result = ai_client.match_jobs(
            {
                "candidate_id": candidate.id,
                "target_title": candidate.target_title,
                "limit": limit,
                "profile_text": candidate.profile_text,
                "skills": candidate.skills,
                "work_modes": filters.get("work_modes"),
                "job_types": filters.get("employment_types"),
                "pay_min": filters.get("pay_min"),
                "pay_period": filters.get("pay_period"),
                "location": candidate.location,
            }
        )
    except Exception:
        return store.job_matches(limit=limit)

    if result.get("source") in {None, "error", "seed_corpus", "unconfigured"}:
        return store.job_matches(limit=limit)

    matches = result.get("matches") or []
    if not isinstance(matches, list):
        return store.job_matches(limit=limit)
    return store.ingest_and_score_live_jobs(matches, limit=limit)


@router.post("/sync")
def sync_jobs(payload: JobSyncBody | None = Body(default=None)) -> dict[str, object]:
    body = payload or JobSyncBody()
    candidate = store.candidate
    store.set_match_filters(
        work_modes=body.work_modes,
        employment_types=body.employment_types,
        pay_min=body.pay_min,
        pay_period=body.pay_period,
    )
    if not candidate.target_title or not str(candidate.target_title).strip():
        return store.sync_jobs()
    if not ai_client.ai_service_reachable():
        return store.sync_jobs()
    try:
        stats = ai_client.fanout_jobs(
            {
                "target_title": candidate.target_title,
                "location": candidate.location,
                "top_skill": candidate.skills[0] if candidate.skills else None,
                "work_modes": body.work_modes,
            }
        )
    except httpx.HTTPStatusError as exc:
        detail = "Live harvest failed"
        try:
            data = exc.response.json()
            if isinstance(data, dict) and data.get("detail"):
                detail = str(data["detail"])
        except Exception:
            detail = exc.response.text[:240] or detail
        if exc.response.status_code == 400:
            raise HTTPException(status_code=400, detail=detail) from exc
        return store.sync_jobs()
    except Exception:
        return store.sync_jobs()

    if stats.get("source") != "xano":
        return store.sync_jobs()
    return store.mark_live_sync(stats)


@router.get("/{job_id}", response_model=Job)
def get_job(job_id: str) -> Job:
    job = store.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Unknown job {job_id}")
    return job
