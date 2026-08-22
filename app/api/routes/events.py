from fastapi import APIRouter

from app.schemas.event import NetworkingEvent

router = APIRouter(prefix="/events", tags=["events"])


@router.get("/matches", response_model=list[NetworkingEvent])
def list_event_matches() -> list[NetworkingEvent]:
    return [
        NetworkingEvent(
            id="event_demo_1",
            name="AI Builders Meetup",
            location="New York, NY",
            format="in-person",
            why_this_event="Speakers and attendees map to your target backend + AI roles.",
            match_percent=91,
        )
    ]
