from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.schemas.application import Application
from app.services.store import store

router = APIRouter(prefix="/applications", tags=["applications"])


class ApplicationCreate(BaseModel):
    job_id: str


class ApplicationStatusUpdate(BaseModel):
    status: str


@router.get("", response_model=list[Application])
def list_applications() -> list[Application]:
    return store.applications()


@router.post("", response_model=Application)
def create_application(payload: ApplicationCreate) -> Application:
    try:
        return store.target_job(payload.job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown job {payload.job_id}") from None
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from None


@router.patch("/{job_id}", response_model=Application)
def update_application(job_id: str, payload: ApplicationStatusUpdate) -> Application:
    application = store.set_application_status(job_id, payload.status)
    if application is None:
        raise HTTPException(status_code=404, detail=f"No application for job {job_id}")
    return application


@router.delete("/{job_id}", status_code=204)
def delete_application(job_id: str) -> None:
    store.untarget_job(job_id)
