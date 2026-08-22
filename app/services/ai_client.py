import httpx

from app.core.config import settings


async def call_agent(path: str, payload: dict) -> dict:
    async with httpx.AsyncClient(base_url=settings.ai_service_url, timeout=60) as client:
        response = await client.post(f"/api/agents/{path}", json=payload)
        response.raise_for_status()
        return response.json()
