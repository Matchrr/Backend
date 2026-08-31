"""Xano Authentication API client (signup, login, auth/me).

User JWTs are issued by Xano. This module talks to the pre-built
`/auth/signup`, `/auth/login`, and `/auth/me` endpoints on the configured
API group. It does not touch the job-catalog client the harvest workstream owns.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings

AUTH_MISSING_DETAIL = (
    "Xano auth endpoints were not found on this API group. In the Xano dashboard, "
    "open the API group used by XANO_API_URL (or XANO_AUTH_API_URL) and add the "
    "pre-built Authentication endpoints: Signup, Login, and Auth/me."
)


class XanoAuthError(Exception):
    def __init__(self, message: str, status_code: int = 400, code: str | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code


@dataclass(frozen=True)
class XanoUser:
    id: str
    email: str | None
    name: str | None
    raw: dict[str, Any]


def auth_base_url() -> str:
    return (settings.xano_auth_api_url or settings.xano_api_url).rstrip("/")


def is_configured() -> bool:
    return bool(auth_base_url())


def signup(email: str, password: str) -> tuple[str, XanoUser]:
    payload = _request("POST", "/auth/signup", json={"email": email, "password": password})
    token = _extract_token(payload)
    user = _extract_user(payload)
    if user is None or not user.email:
        user = fetch_me(token)
    return token, user


def login(email: str, password: str) -> tuple[str, XanoUser]:
    payload = _request("POST", "/auth/login", json={"email": email, "password": password})
    token = _extract_token(payload)
    user = _extract_user(payload)
    if user is None or not user.email:
        user = fetch_me(token)
    return token, user


def fetch_me(token: str) -> XanoUser:
    payload = _request("GET", "/auth/me", token=token)
    user = _extract_user(payload)
    if user is None:
        raise XanoAuthError("Xano /auth/me did not return a user record.", status_code=502)
    return user


def endpoints_available() -> bool:
    """True when Login/Signup/Auth-me exist on the API group.

    GET /auth/me without a token is 401/403 when the endpoint exists, and 404
    when this API group has no Authentication endpoints yet.
    """
    base = auth_base_url()
    if not base:
        return False
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{base}/auth/me")
    except httpx.HTTPError:
        return False
    return response.status_code != 404


def _request(
    method: str,
    path: str,
    *,
    json: dict[str, Any] | None = None,
    token: str | None = None,
) -> Any:
    base = auth_base_url()
    if not base:
        raise XanoAuthError(
            "Xano is not configured. Set XANO_API_URL (and optionally XANO_AUTH_API_URL).",
            status_code=503,
        )

    headers: dict[str, str] = {}
    if json is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        with httpx.Client(timeout=20.0) as client:
            response = client.request(method, f"{base}{path}", json=json, headers=headers)
    except httpx.HTTPError as exc:
        raise XanoAuthError(f"Cannot reach Xano at {base}.", status_code=503) from exc

    if response.status_code == 404:
        raise XanoAuthError(AUTH_MISSING_DETAIL, status_code=503, code="auth_endpoints_missing")

    if response.status_code >= 400:
        raise XanoAuthError(_error_message(response), status_code=_client_status(response.status_code))

    if not response.content:
        return {}
    try:
        return response.json()
    except ValueError as exc:
        raise XanoAuthError("Xano returned a non-JSON response.", status_code=502) from exc


def _client_status(status: int) -> int:
    if status in {401, 403}:
        return 401
    if status in {409, 422, 429}:
        return status
    if 400 <= status < 500:
        return 400
    return 502


def _error_message(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return f"Xano auth failed ({response.status_code})."
    if isinstance(payload, dict):
        message = payload.get("message") or payload.get("detail")
        if isinstance(message, str) and message.strip():
            return message
    return f"Xano auth failed ({response.status_code})."


def _extract_token(payload: Any) -> str:
    if isinstance(payload, str) and payload.count(".") >= 2:
        return payload
    if not isinstance(payload, dict):
        raise XanoAuthError("Xano did not return an auth token.", status_code=502)
    for key in ("authToken", "auth_token", "AuthToken", "token"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    raise XanoAuthError("Xano did not return an auth token.", status_code=502)


def _extract_user(payload: Any) -> XanoUser | None:
    if not isinstance(payload, dict):
        return None
    record = payload.get("user") if isinstance(payload.get("user"), dict) else payload
    if not isinstance(record, dict):
        return None
    raw_id = record.get("id", record.get("user_id"))
    if raw_id is None:
        return None
    name = record.get("name") or record.get("full_name")
    if isinstance(name, str):
        name = name.strip() or None
    email = record.get("email")
    return XanoUser(
        id=str(raw_id),
        email=email if isinstance(email, str) else None,
        name=name if isinstance(name, str) else None,
        raw=record,
    )


def user_to_dict(user: XanoUser) -> dict[str, Any]:
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "created_at": user.raw.get("created_at"),
    }
