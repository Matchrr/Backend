from fastapi import APIRouter, File, UploadFile

from app.schemas.candidate import Candidate, CandidateCreate

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.post("", response_model=Candidate)
def create_candidate(payload: CandidateCreate) -> Candidate:
    return Candidate(
        id="candidate_demo",
        target_title=payload.target_title,
        location=payload.location,
        linkedin_connected=payload.linkedin_connected,
    )


@router.post("/resume", response_model=Candidate)
async def upload_resume(file: UploadFile = File(...)) -> Candidate:
    _ = file.filename
    return Candidate(
        id="candidate_demo",
        headline="Resume uploaded — grounding pending",
    )


@router.get("/me", response_model=Candidate)
def get_current_candidate() -> Candidate:
    return Candidate(
        id="candidate_demo",
        headline="Connect LinkedIn or upload a resume to ground your profile",
        skills=[],
    )
