"""Sign in with Google (OpenID Connect). Separate from Gmail send scopes."""

from __future__ import annotations

import secrets
import threading
import time
from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import settings

AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
SCOPES = ("openid", "email", "profile")
STATE_TTL_SECONDS = 600


class GoogleAuthError(Exception):
    def __init__(self, message: str, *, code: str = "google_auth_error") -> None:
        super().__init__(message)
        self.code = code


class _PendingAuth:
    __slots__ = ("created_at",)

    def __init__(self) -> None:
        self.created_at = time.time()


_pending: dict[str, _PendingAuth] = {}
_lock = threading.Lock()


def is_configured() -> bool:
    return bool(
        settings.google_client_id.strip()
        and settings.google_client_secret.strip()
        and settings.google_redirect_uri.strip()
    )


def build_authorization_url() -> str:
    if not is_configured():
        raise GoogleAuthError(
            "Google sign-in is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
            code="not_configured",
        )

    state = secrets.token_urlsafe(24)
    with _lock:
        _evict_expired_locked()
        _pending[state] = _PendingAuth()

    params = {
        "response_type": "code",
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "scope": " ".join(SCOPES),
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return f"{AUTHORIZE_URL}?{urlencode(params)}"


def complete_login(code: str | None, state: str | None) -> dict[str, str]:
    """Exchange the OAuth code and return email, name, and Google subject."""
    if not code or not state:
        raise GoogleAuthError("Google did not return an authorization code.", code="missing_code")

    with _lock:
        pending = _pending.pop(state, None)
        _evict_expired_locked()

    if pending is None or time.time() - pending.created_at > STATE_TTL_SECONDS:
        raise GoogleAuthError("This Google sign-in expired. Please try again.", code="invalid_state")

    tokens = _exchange_code(code)
    access_token = tokens.get("access_token")
    if not isinstance(access_token, str) or not access_token:
        raise GoogleAuthError("Google did not return an access token.", code="missing_token")

    profile = _fetch_userinfo(access_token)
    email = profile.get("email")
    if not isinstance(email, str) or not email:
        raise GoogleAuthError("Google did not share an email address.", code="missing_email")
    if profile.get("email_verified") is False:
        raise GoogleAuthError("Google has not verified this email address.", code="unverified_email")

    google_id = profile.get("sub")
    if not isinstance(google_id, str) or not google_id:
        raise GoogleAuthError("Google did not return a user id.", code="missing_sub")

    name = profile.get("name")
    if not isinstance(name, str) or not name.strip():
        name = email.split("@", 1)[0]

    return {"email": email.strip().lower(), "name": name.strip(), "google_id": google_id}


def random_account_password() -> str:
    return f"{secrets.token_urlsafe(18)}Aa1"


def _exchange_code(code: str) -> dict[str, Any]:
    try:
        with httpx.Client(timeout=20.0) as client:
            response = client.post(
                TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": settings.google_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
    except httpx.HTTPError as exc:
        raise GoogleAuthError("Could not reach Google to finish sign-in.") from exc

    if response.status_code >= 400:
        raise GoogleAuthError("Google rejected this sign-in. Please try again.", code="token_error")

    payload = response.json()
    if not isinstance(payload, dict):
        raise GoogleAuthError("Google returned an unexpected token response.")
    return payload


def _fetch_userinfo(access_token: str) -> dict[str, Any]:
    try:
        with httpx.Client(timeout=20.0) as client:
            response = client.get(
                USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
    except httpx.HTTPError as exc:
        raise GoogleAuthError("Could not reach Google for the account profile.") from exc

    if response.status_code >= 400:
        raise GoogleAuthError("Google would not share this account profile.", code="userinfo_error")

    payload = response.json()
    if not isinstance(payload, dict):
        raise GoogleAuthError("Google returned an unexpected profile.")
    return payload


def _evict_expired_locked() -> None:
    now = time.time()
    expired = [key for key, pending in _pending.items() if now - pending.created_at > STATE_TTL_SECONDS]
    for key in expired:
        _pending.pop(key, None)
