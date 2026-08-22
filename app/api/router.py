from fastapi import APIRouter

from app.api.routes import (
    applications,
    candidates,
    events,
    growth,
    health,
    integrations,
    jobs,
    outreach,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(candidates.router)
api_router.include_router(jobs.router)
api_router.include_router(applications.router)
api_router.include_router(events.router)
api_router.include_router(growth.router)
api_router.include_router(integrations.router)
api_router.include_router(outreach.router)
