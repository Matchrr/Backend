from fastapi import APIRouter

from app.schemas.job import FitScorecard, Job

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/matches", response_model=list[Job])
def list_job_matches() -> list[Job]:
    return [
        Job(
            id="job_demo_1",
            title="Senior Software Engineer",
            company="Example Labs",
            location="Remote",
            source="Google Jobs",
            scorecard=FitScorecard(
                match_percent=86,
                matching_skills=["Python", "FastAPI"],
                missing_tech=["Kubernetes"],
                key_angle="Strong backend depth; highlight distributed systems work.",
            ),
        )
    ]
