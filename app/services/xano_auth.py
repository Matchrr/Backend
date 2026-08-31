"""Xano Authentication API client (signup, login, me, password reset).

User JWTs are issued by Xano. This module talks to the Authentication API
group: `/auth/signup`, `/auth/login`, `/auth/me`, and the Quick Start reset
flow (`/reset/request-reset-link`, `/reset/magic-link-login`,
`/reset/update_password`). It does not touch the job-catalog client the
harvest workstream owns.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings

AUTH_MISSING_DETAIL = (
    "Xano auth endpoints were not found on this API group. In the Xano dashboard, "
    "open the API group used by XANO_API_URL (or XANO_AUTH_API_URL) and add the "
    "Authentication endpoints: Signup, Login, Auth/me, and the password-reset "
    "trio (request-reset-link, magic-link-login, update_password)."
)

RESET_LINK_INVALID = (
    "This reset link is invalid or has expired. Request a new one from the sign-in page."
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


def login_with_google(email: str, name: str, google_id: str, password: str) -> tuple[str, XanoUser]:
    """Return the Xano session for a Google-verified identity.

    Xano `/auth/google` must reuse the existing email row when one exists so
    LinkedIn/resume data stays on the same user_id. A new row is created only
    when that email has never signed up.
    """
    payload = _request(
        "POST",
        "/auth/google",
        json={
            "email": email.strip().lower(),
            "name": name,
            "google_id": google_id,
            "password": password,
            "secret": settings.matchr_service_secret,
        },
    )
    token = _extract_token(payload)
    user = _extract_user(payload)
    if user is None or not user.email:
        user = fetch_me(token)
    return token, user


def request_password_reset(email: str, origin: str | None = None) -> None:
    """Send a one-time reset link. Always succeeds unless Xano is unreachable.

    Unknown emails return the same ok as known ones so the client cannot
    enumerate accounts. The magic link lands on `{origin}/reset-password`.
    """
    params: dict[str, Any] = {"email": email}
    if origin:
        params["origin"] = origin.rstrip("/")
    try:
        _request("GET", "/reset/request-reset-link", params=params)
    except XanoAuthError as exc:
        if exc.code == "auth_endpoints_missing":
            raise
        if exc.status_code in {400, 404}:
            return
        raise


def reset_password(email: str, magic_token: str, password: str) -> tuple[str, XanoUser]:
    """Exchange the email token for a session, then set the new password."""
    assert_password_policy(password)
    try:
        payload = _request(
            "POST",
            "/reset/magic-link-login",
            json={"email": email, "magic_token": magic_token},
        )
    except XanoAuthError as exc:
        raise _rewrite_reset_error(exc) from exc
    token = _extract_token(payload)
    _request(
        "POST",
        "/reset/update_password",
        json={"password": password, "confirm_password": password},
        token=token,
    )
    user = _extract_user(payload)
    if user is None or not user.email:
        user = fetch_me(token)
    return token, user


def assert_password_policy(password: str) -> None:
    if len(password) < 8:
        raise XanoAuthError("Password must be at least 8 characters.", status_code=400)
    if not any(character.isalpha() for character in password):
        raise XanoAuthError("Password must include a letter.", status_code=400)
    if not any(character.isdigit() for character in password):
        raise XanoAuthError("Password must include a number.", status_code=400)


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
    params: dict[str, Any] | None = None,
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
            response = client.request(
                method,
                f"{base}{path}",
                json=json,
                params=params,
                headers=headers,
            )
    except httpx.HTTPError as exc:
        raise XanoAuthError(f"Cannot reach Xano at {base}.", status_code=503) from exc

    if response.status_code == 404:
        message = _error_message(response)
        if _is_missing_route(message, response):
            raise XanoAuthError(AUTH_MISSING_DETAIL, status_code=503, code="auth_endpoints_missing")
        raise XanoAuthError(message, status_code=404)

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


def _is_missing_route(message: str, response: httpx.Response) -> bool:
    lowered = message.lower()
    if "unable to locate request" in lowered or "not found on this api" in lowered:
        return True
    if not response.content:
        return True
    return lowered in {"xano auth failed (404).", "404 not found"}


def _rewrite_reset_error(exc: XanoAuthError) -> XanoAuthError:
    if exc.code == "auth_endpoints_missing":
        return exc
    lowered = str(exc).lower()
    needles = (
        "token did not match",
        "magic token has expired",
        "already been used",
        "password_reset.token",
        "magic_token is required",
    )
    if any(needle in lowered for needle in needles):
        return XanoAuthError(RESET_LINK_INVALID, status_code=400)
    return exc


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
