"""Demand snapshot for the standing harvest worker."""

from __future__ import annotations

import re

from app.services.career_parse import city_only_location
from app.services.store import store

_SENIORITY = {
    "junior",
    "jr",
    "senior",
    "sr",
    "staff",
    "principal",
    "lead",
    "intern",
    "associate",
    "mid",
    "mid-level",
    "entry",
    "entry-level",
}

_FAMILY_TITLES = {
    "software engineer": "software_engineering",
    "backend engineer": "software_engineering",
    "frontend engineer": "software_engineering",
    "full stack engineer": "software_engineering",
    "mobile engineer": "software_engineering",
    "devops engineer": "software_engineering",
    "qa engineer": "software_engineering",
    "data scientist": "data_ml",
    "machine learning engineer": "data_ml",
    "data engineer": "data_ml",
    "product manager": "product",
    "technical program manager": "product",
    "product designer": "design",
    "ux designer": "design",
    "sales engineer": "go_to_market",
    "customer success manager": "go_to_market",
    "marketing manager": "go_to_market",
    "business analyst": "ops",
    "it support specialist": "ops",
    "security engineer": "ops",
}

_ALIASES = {
    "swe": "software_engineering",
    "software engineering": "software_engineering",
    "software developer": "software_engineering",
    "backend developer": "software_engineering",
    "frontend developer": "software_engineering",
}


def _strip_seniority(title: str) -> str:
    tokens = re.sub(r"[/]+", " ", title.lower()).split()
    kept = [token for token in tokens if token not in _SENIORITY]
    return " ".join(kept).strip() or title.lower().strip()


def title_to_family(raw: str) -> str:
    cleaned = _strip_seniority(raw)
    if cleaned in _FAMILY_TITLES:
        return _FAMILY_TITLES[cleaned]
    if cleaned in _ALIASES:
        return _ALIASES[cleaned]
    for title, family in _FAMILY_TITLES.items():
        if title in cleaned or cleaned in title:
            return family
    return cleaned or "unknown"


def harvest_demand() -> dict[str, object]:
    candidate = store.candidate
    titles: list[dict[str, object]] = []
    locations: list[dict[str, object]] = []
    user_count = 0
    if candidate.target_title:
        user_count = 1
        titles.append(
            {
                "raw": candidate.target_title,
                "family": title_to_family(candidate.target_title),
                "count": 1,
            }
        )
    if candidate.location:
        loc = city_only_location(candidate.location) or candidate.location
        loc = loc.strip().lower()
        if loc:
            locations.append({"normalized": loc, "count": 1})
    return {"titles": titles, "locations": locations, "user_count": user_count}
