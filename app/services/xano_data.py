"""HTTP client for Matchr Xano tables (profiles, source documents, later packages)."""

from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

import httpx

from app.core.config import settings

_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


class XanoDataError(RuntimeError):
    pass


def configured() -> bool:
    return bool(settings.xano_api_url)


def list_records(table: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    page = 1
    per_page = 100
    while page <= 50:
        query = {"page": page, "per_page": per_page, **(params or {})}
        data = request("GET", table, params=query)
        batch = _unwrap(data)
        if not batch:
            break
        existing = {row.get("id") for row in items}
        if page > 1 and all(row.get("id") in existing for row in batch):
            break
        items.extend(batch)
        if len(batch) < per_page:
            break
        page += 1
    return items


def get(table: str, record_id: int | str) -> dict[str, Any] | None:
    data = request("GET", f"{table}/{record_id}")
    return data if isinstance(data, dict) else None


def add(table: str, payload: dict[str, Any]) -> dict[str, Any]:
    data = request("POST", table, json=payload)
    if not isinstance(data, dict):
        raise XanoDataError(f"Xano POST {table} returned no record")
    return data


def patch(table: str, record_id: int | str, payload: dict[str, Any]) -> dict[str, Any]:
    data = request("PATCH", f"{table}/{record_id}", json=payload)
    return data if isinstance(data, dict) else {"id": record_id, **payload}


def delete(table: str, record_id: int | str) -> None:
    request("DELETE", f"{table}/{record_id}")


def request(method: str, path: str, **kwargs: Any) -> Any:
    if not configured():
        raise XanoDataError("XANO_API_URL is not set")
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if settings.xano_api_key:
        headers["Authorization"] = f"Bearer {settings.xano_api_key}"
    url = urljoin(settings.xano_api_url.rstrip("/") + "/", path.lstrip("/"))
    try:
        response = httpx.request(method, url, headers=headers, timeout=_TIMEOUT, **kwargs)
    except httpx.HTTPError as exc:
        raise XanoDataError(f"Xano {method} {path} failed: {exc}") from exc
    if response.status_code >= 400:
        raise XanoDataError(f"Xano {method} {path} → {response.status_code}: {response.text[:400]}")
    if not response.content:
        return None
    try:
        return response.json()
    except ValueError:
        return None


def _unwrap(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [row for row in data if isinstance(row, dict)]
    if isinstance(data, dict):
        for key in ("items", "payload", "records", "result"):
            value = data.get(key)
            if isinstance(value, list):
                return [row for row in value if isinstance(row, dict)]
    return []
