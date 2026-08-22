from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/integrations", tags=["integrations"])


class IntegrationStatus(BaseModel):
    provider: str
    connected: bool
    auth_url: str | None = None


@router.get("", response_model=list[IntegrationStatus])
def list_integrations() -> list[IntegrationStatus]:
    return [
        IntegrationStatus(provider="linkedin", connected=False, auth_url="/api/integrations/linkedin/start"),
        IntegrationStatus(provider="gmail", connected=False, auth_url="/api/integrations/gmail/start"),
    ]


@router.get("/linkedin/start")
def start_linkedin_oauth() -> dict[str, str]:
    return {"provider": "linkedin", "status": "not_configured"}


@router.get("/gmail/start")
def start_gmail_oauth() -> dict[str, str]:
    return {"provider": "gmail", "status": "not_configured"}
