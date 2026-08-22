from fastapi import APIRouter

from app.schemas.growth import GrowthPlan, LearningResource, SkillGap

router = APIRouter(prefix="/growth", tags=["growth"])


@router.get("/plan", response_model=GrowthPlan)
def get_growth_plan() -> GrowthPlan:
    return GrowthPlan(
        target_title="Senior Software Engineer",
        skill_gaps=[
            SkillGap(
                skill="Kubernetes",
                priority=1,
                resources=[
                    LearningResource(
                        title="Kubernetes for the Absolute Beginner",
                        kind="course",
                        url="https://www.youtube.com/results?search_query=kubernetes+beginner",
                        provider="YouTube",
                        why="Frequently listed on roles matching your target title.",
                    )
                ],
            )
        ],
    )
