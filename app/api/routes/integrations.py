from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.services.store import store

router = APIRouter(prefix="/integrations", tags=["integrations"])


class IntegrationStatus(BaseModel):
    provider: str
    label: str
    direction: str
    connected: bool
    configured: bool
    description: str


class ConnectRequest(BaseModel):
    connected: bool = True


@router.get("", response_model=list[IntegrationStatus])
def list_integrations() -> list[IntegrationStatus]:
    return [
        IntegrationStatus(
            provider="linkedin",
            label="LinkedIn",
            direction="inbound",
            connected=store.candidate.linkedin_connected,
            configured=bool(settings.linkedin_client_id and settings.linkedin_client_secret),
            description="Pulls headline, experience, skills, and education into your profile.",
        ),
        IntegrationStatus(
            provider="gmail",
            label="Gmail",
            direction="outbound",
            connected=store.candidate.gmail_connected,
            configured=bool(settings.gmail_client_id and settings.gmail_client_secret),
            description="Sends approved outreach from your own inbox. Never sends on its own.",
        ),
    ]


@router.post("/{provider}/connect", response_model=list[IntegrationStatus])
def connect_integration(provider: str, payload: ConnectRequest) -> list[IntegrationStatus]:
    """Simulated OAuth consent.

    Real credentials are not configured in the MVP, so this flips local state to
    exercise the downstream flows.
    """
    if provider == "gmail":
        store.update_candidate(gmail_connected=payload.connected)
    elif provider == "linkedin":
        store.update_candidate(linkedin_connected=payload.connected)
    else:
        raise HTTPException(status_code=404, detail=f"Unknown provider {provider}")
    return list_integrations()
