from fastapi import APIRouter, Query

from app.schemas.overview import ActivityEntry, Overview
from app.services.store import store

router = APIRouter(prefix="/overview", tags=["overview"])


@router.get("", response_model=Overview)
def get_overview() -> Overview:
    """Everything the dashboard renders, derived in one pass."""
    return store.overview()


@router.get("/activity", response_model=list[ActivityEntry])
def get_activity(limit: int = Query(default=20, ge=1, le=40)) -> list[ActivityEntry]:
    return store.activity(limit)
