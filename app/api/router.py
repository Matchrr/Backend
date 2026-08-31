from fastapi import APIRouter

from app.api.routes import (
    applications,
    auth,
    candidates,
    dossier,
    events,
    growth,
    health,
    integrations,
    internal,
    jobs,
    outreach,
    overview,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(internal.router)
api_router.include_router(overview.router)
api_router.include_router(candidates.router)
api_router.include_router(jobs.router)
api_router.include_router(applications.router)
api_router.include_router(dossier.router)
api_router.include_router(events.router)
api_router.include_router(growth.router)
api_router.include_router(integrations.router)
api_router.include_router(outreach.router)
