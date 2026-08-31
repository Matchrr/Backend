from fastapi import APIRouter, Header, HTTPException

from app.core.config import settings
from app.services.harvest import harvest_demand

router = APIRouter(prefix="/internal", tags=["internal"])


@router.get("/harvest-demand")
def get_harvest_demand(
    x_matchr_service_secret: str | None = Header(default=None, alias="X-Matchr-Service-Secret"),
) -> dict[str, object]:
    expected = settings.matchr_service_secret
    if expected and (x_matchr_service_secret or "") != expected:
        raise HTTPException(status_code=403, detail="Forbidden")
    return harvest_demand()
