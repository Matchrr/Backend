import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def parse_xano_user_id(candidate_id: str | None) -> int | None:
    try:
        value = int(str(candidate_id or "").strip())
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


async def call_agent(path: str, payload: dict) -> dict:
    async with httpx.AsyncClient(base_url=settings.ai_service_url, timeout=60) as client:
        response = await client.post(f"/api/agents/{path}", json=payload)
        response.raise_for_status()
        return response.json()


def post_json(path: str, payload: dict, timeout: float = 60) -> dict:
    with httpx.Client(base_url=settings.ai_service_url, timeout=timeout) as client:
        response = client.post(path, json=payload)
        response.raise_for_status()
        data = response.json()
        return data if isinstance(data, dict) else {"data": data}


def fanout_jobs(payload: dict) -> dict:
    return post_json("/api/pipelines/jobs/fanout", payload, timeout=120)


def match_jobs(payload: dict) -> dict:
    return post_json("/api/agents/match", payload, timeout=60)


def sync_profile_chunks(payload: dict) -> dict:
    return post_json("/api/pipelines/profile/chunks", payload, timeout=90)


def generate_cover_letter(payload: dict) -> dict:
    return post_json("/api/agents/tailor", payload, timeout=90)


def ai_service_reachable() -> bool:
    return bool(settings.ai_service_url)
