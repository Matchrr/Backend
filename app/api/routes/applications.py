from fastapi import APIRouter
from pydantic import BaseModel

from app.schemas.application import Application

router = APIRouter(prefix="/applications", tags=["applications"])


class ApplicationCreate(BaseModel):
    job_id: str


@router.post("", response_model=Application)
def create_application(payload: ApplicationCreate) -> Application:
    return Application(
        id="app_demo_1",
        candidate_id="candidate_demo",
        job_id=payload.job_id,
        status="draft",
    )


@router.get("", response_model=list[Application])
def list_applications() -> list[Application]:
    return []
