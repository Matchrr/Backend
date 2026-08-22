"""Career Growth Advisor.

Deliberately not a resume critique. It treats the grounded profile and the
target role as a gap-analysis problem: which skills are being asked for by the
live postings the candidate already matches, and what closes each gap.
"""

from __future__ import annotations

from app.data.seed import RESOURCE_LIBRARY
from app.data.skills import core_skills_for_title
from app.schemas.candidate import Candidate
from app.schemas.growth import GrowthPlan, LearningResource, SkillGap
from app.schemas.job import Job

MAX_GAPS = 6
MAX_RESOURCES_PER_GAP = 4

# Gaps are only counted from postings the candidate is actually competitive for.
# Without this, a poorly-matched frontend role would tell a backend engineer to
# go learn TypeScript.
MIN_RELEVANT_MATCH = 55
RELEVANCE_WINDOW = 20


def _relevant_jobs(scored_jobs: list[Job]) -> list[Job]:
    scored = [job for job in scored_jobs if job.scorecard]
    if not scored:
        return []
    best = max(job.scorecard.match_percent for job in scored)
    threshold = max(MIN_RELEVANT_MATCH, best - RELEVANCE_WINDOW)
    return [job for job in scored if job.scorecard.match_percent >= threshold]


def build_growth_plan(candidate: Candidate, scored_jobs: list[Job]) -> GrowthPlan:
    if not candidate.grounded:
        return GrowthPlan(
            target_title=candidate.target_title,
            summary=(
                "Connect LinkedIn or upload a resume first. The growth plan is computed "
                "against your verified history, so there is nothing to compare yet."
            ),
        )

    owned = {skill.lower() for skill in candidate.skills}
    relevant = _relevant_jobs(scored_jobs)

    # Demand = how many live matched postings ask for a skill the profile lacks.
    demand: dict[str, int] = {}
    companies: dict[str, list[str]] = {}
    for job in relevant:
        for skill in job.scorecard.missing_tech:
            demand[skill] = demand.get(skill, 0) + 1
            companies.setdefault(skill, []).append(job.company)

    # Role baseline covers skills the market expects even if today's postings
    # happen not to mention them.
    for skill in core_skills_for_title(candidate.target_title):
        if skill.lower() not in owned:
            demand.setdefault(skill, 0)
            demand[skill] += 1
            companies.setdefault(skill, [])

    ranked = sorted(demand.items(), key=lambda item: (-item[1], item[0]))[:MAX_GAPS]

    gaps = [
        SkillGap(
            skill=skill,
            priority=position + 1,
            demand_count=count,
            demand_note=_demand_note(count, companies.get(skill, [])),
            resources=_resources_for(skill, candidate.target_title, count),
        )
        for position, (skill, count) in enumerate(ranked)
    ]

    return GrowthPlan(
        target_title=candidate.target_title,
        summary=_summary(candidate, gaps, scored_jobs),
        strengths=_strengths(candidate, relevant),
        skill_gaps=gaps,
    )


def gap_skills(plan: GrowthPlan) -> list[str]:
    return [gap.skill for gap in plan.skill_gaps]


def _demand_note(count: int, companies: list[str]) -> str:
    unique = list(dict.fromkeys(companies))
    if not unique:
        return "Expected baseline for your target role, even though today's matches skip it."
    if count == 1:
        return f"Listed on your {unique[0]} match."
    shown = ", ".join(unique[:3])
    suffix = f" and {len(unique) - 3} more" if len(unique) > 3 else ""
    return f"Requested by {count} of your live matches — {shown}{suffix}."


def _resources_for(skill: str, target_title: str | None, demand_count: int) -> list[LearningResource]:
    entries = RESOURCE_LIBRARY.get(skill, [])
    goal = target_title or "your target role"
    resources: list[LearningResource] = []
    seen_kinds: dict[str, int] = {}
    for entry in entries[:MAX_RESOURCES_PER_GAP]:
        kind = entry["kind"]
        rank = seen_kinds.get(kind, 0)
        seen_kinds[kind] = rank + 1
        resources.append(
            LearningResource(
                title=entry["title"],
                kind=kind,
                url=entry["url"],
                provider=entry.get("provider"),
                why=_resource_reason(kind, skill, goal, demand_count, rank),
            )
        )
    if not resources:
        resources.append(
            LearningResource(
                title=f"Search high-signal {skill} material",
                kind="search",
                url=f"https://www.google.com/search?q={skill.replace(' ', '+')}+for+engineers",
                provider="Web",
                why=f"No curated pack for {skill} yet — start from primary sources.",
            )
        )
    return resources


# Second and later resources of the same kind get a different rationale so a
# skill with two books does not show the same sentence twice.
_REASON_VARIANTS: dict[str, list[str]] = {
    "certification": [
        "A credential recruiters can filter on when screening for {goal}.",
        "Second credential option — pick whichever your target companies cite more often.",
    ],
    "video": [
        "Fastest way to get hands on {skill} this week without a paid enrollment.",
        "Another free walkthrough if the first one's pace does not suit you.",
    ],
    "docs": [
        "Primary source — what you will actually reach for once you are writing {skill}.",
        "Reference material for the details tutorials skip.",
    ],
    "reading": [
        "Builds the depth interviewers probe for beyond surface {skill} familiarity.",
        "Longer commitment, but it is the source most {skill} interview questions trace back to.",
    ],
    "course": [
        "Structured path to close the {skill} gap for {goal}.",
        "Alternative structured path if you prefer a different teaching style.",
    ],
}


def _resource_reason(kind: str, skill: str, goal: str, demand_count: int, rank: int = 0) -> str:
    variants = _REASON_VARIANTS.get(kind)
    if not variants:
        return f"Useful primary material for {skill}."
    if kind == "course" and rank == 0 and demand_count > 1:
        return f"Structured path to {skill}, which {demand_count} of your live matches require."
    return variants[min(rank, len(variants) - 1)].format(skill=skill, goal=goal)


def _strengths(candidate: Candidate, scored_jobs: list[Job]) -> list[str]:
    counts: dict[str, int] = {}
    for job in scored_jobs:
        if not job.scorecard:
            continue
        for skill in job.scorecard.matching_skills:
            counts[skill] = counts.get(skill, 0) + 1
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    if ranked:
        return [skill for skill, _ in ranked[:6]]
    return candidate.skills[:6]


def _summary(candidate: Candidate, gaps: list[SkillGap], scored_jobs: list[Job]) -> str:
    goal = candidate.target_title or "your target role"
    if not gaps:
        return f"No material gaps detected between your profile and {goal}. Focus on applying."
    top = ", ".join(gap.skill for gap in gaps[:3])
    if scored_jobs:
        best = max(job.scorecard.match_percent for job in scored_jobs if job.scorecard)
        return (
            f"Your strongest live match sits at {best}%. Closing {top} is what moves that "
            f"number for {goal} — these are capability gaps, not wording problems."
        )
    return f"Closing {top} is what moves your fit for {goal}."
