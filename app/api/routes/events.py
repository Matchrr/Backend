from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.schemas.event import NetworkingEvent
from app.services.store import store

router = APIRouter(prefix="/events", tags=["events"])


class EventSaveRequest(BaseModel):
    saved: bool = True


@router.get("/matches", response_model=list[NetworkingEvent])
def list_event_matches(limit: int = Query(8, ge=1, le=50)) -> list[NetworkingEvent]:
    return store.event_matches(limit=limit)


@router.post("/{event_id}/save", response_model=list[NetworkingEvent])
def save_event(event_id: str, payload: EventSaveRequest) -> list[NetworkingEvent]:
    try:
        store.toggle_saved_event(event_id, payload.saved)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Unknown event {event_id}") from None
    return store.event_matches()
