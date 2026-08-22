from fastapi import APIRouter

from app.schemas.growth import GrowthPlan
from app.services.store import store

router = APIRouter(prefix="/growth", tags=["growth"])


@router.get("/plan", response_model=GrowthPlan)
def get_growth_plan() -> GrowthPlan:
    return store.growth_plan()
