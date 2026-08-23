from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from app.core.config import settings
from app.services import linkedin as linkedin_service
from app.services import nutrient as nutrient_service
from app.services.grounding import ground_from_linkedin, merge_profiles
from app.services.store import store

router = APIRouter(prefix="/integrations", tags=["integrations"])


class IntegrationStatus(BaseModel):
    provider: str
    label: str
    direction: str
    connected: bool
    configured: bool
    description: str
    callback_url: str | None = None
    connectable: bool = True


class ConnectRequest(BaseModel):
    connected: bool = True


class LinkedInAuthorizeResponse(BaseModel):
    url: str
    configured: bool
    scopes: list[str]


@router.get("", response_model=list[IntegrationStatus])
def list_integrations() -> list[IntegrationStatus]:
    return [
        IntegrationStatus(
            provider="linkedin",
            label="LinkedIn",
            direction="inbound",
            connected=store.candidate.linkedin_connected,
            configured=linkedin_service.is_configured(),
            description="Pulls identity, and career history when LinkedIn allows it, into your profile.",
            callback_url=settings.linkedin_redirect_uri,
        ),
        IntegrationStatus(
            provider="gmail",
            label="Gmail",
            direction="outbound",
            connected=store.candidate.gmail_connected,
            configured=bool(settings.gmail_client_id and settings.gmail_client_secret),
            description="Sends approved outreach from your own inbox. Never sends on its own.",
        ),
        IntegrationStatus(
            provider="nutrient",
            label="Nutrient",
            direction="ingest",
            connected=nutrient_service.is_configured(),
            configured=nutrient_service.is_configured(),
            description="OCR and structured extraction for LinkedIn PDFs and resumes.",
            connectable=False,
        ),
    ]


@router.post("/{provider}/connect", response_model=list[IntegrationStatus])
def connect_integration(provider: str, payload: ConnectRequest) -> list[IntegrationStatus]:
    """Simulated OAuth consent for providers that are not configured.

    LinkedIn uses /linkedin/authorize when credentials exist. Disconnect still
    works here so the user can drop the connection without wiping the profile.
    """
    if provider == "gmail":
        store.update_candidate(gmail_connected=payload.connected)
    elif provider == "linkedin":
        if payload.connected and linkedin_service.is_configured():
            raise HTTPException(
                status_code=409,
                detail="LinkedIn OAuth is configured. Use Sign in with LinkedIn instead.",
            )
        updates: dict[str, object] = {"linkedin_connected": payload.connected}
        if not payload.connected:
            updates["linkedin_coverage"] = "none"
        store.update_candidate(**updates)
    else:
        raise HTTPException(status_code=404, detail=f"Unknown provider {provider}")
    return list_integrations()


@router.get("/linkedin/authorize", response_model=LinkedInAuthorizeResponse)
def linkedin_authorize() -> LinkedInAuthorizeResponse:
    try:
        url = linkedin_service.build_authorization_url()
    except linkedin_service.LinkedInError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return LinkedInAuthorizeResponse(
        url=url,
        configured=True,
        scopes=linkedin_service.requested_scopes(),
    )


@router.get("/linkedin/callback")
def linkedin_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
) -> RedirectResponse:
    frontend = settings.frontend_url.rstrip("/")
    if error:
        reason = error_description or error
        return _profile_redirect(frontend, "error", reason)

    try:
        payload, tokens = linkedin_service.complete_login(code, state)
    except linkedin_service.LinkedInError as exc:
        return _profile_redirect(frontend, "error", str(exc))

    incoming = ground_from_linkedin(payload, store.candidate.target_title)
    if store.candidate.grounded or store.candidate.linkedin_connected or store.candidate.full_name:
        store.set_candidate(merge_profiles(store.candidate, incoming))
    else:
        store.set_candidate(incoming)
    store.set_linkedin_tokens(tokens)

    status = "imported" if incoming.linkedin_coverage == "profile" else "identity"
    return _profile_redirect(frontend, status)


def _profile_redirect(frontend: str, status: str, reason: str | None = None) -> RedirectResponse:
    query = {"linkedin": status}
    if reason:
        query["reason"] = reason[:180]
    return RedirectResponse(f"{frontend}/profile?{urlencode(query)}", status_code=302)
