"""Request-scoped Xano identity.

Validates user JWTs against Xano `/auth/me` (with a short cache) and decides
whether protected FastAPI routes should require a session.
"""

from __future__ import annotations

import threading
import time
from typing import Any

from fastapi import Request

from app.core.config import settings
from app.services.xano_auth import XanoAuthError, XanoUser, endpoints_available, fetch_me, is_configured

_CACHE_TTL_SECONDS = 30.0
_lock = threading.Lock()
_user_cache: dict[str, tuple[float, XanoUser]] = {}
_probe: tuple[float, bool] | None = None
_PROBE_TTL_SECONDS = 60.0


def auth_status() -> dict[str, Any]:
    configured = is_configured()
    available = _auth_endpoints_available() if configured else False
    return {
        "provider": "xano",
        "configured": configured,
        "available": available,
        "required": _auth_required(configured, available),
    }


def auth_is_required() -> bool:
    status = auth_status()
    return bool(status["required"])


def bearer_token(request: Request) -> str | None:
    header = request.headers.get("authorization") or request.headers.get("Authorization")
    if not header:
        return None
    scheme, _, value = header.partition(" ")
    if scheme.lower() != "bearer" or not value.strip():
        return None
    return value.strip()


def resolve_user(token: str) -> XanoUser:
    now = time.monotonic()
    with _lock:
        cached = _user_cache.get(token)
        if cached and cached[0] > now:
            return cached[1]
    user = fetch_me(token)
    with _lock:
        _user_cache[token] = (now + _CACHE_TTL_SECONDS, user)
        if len(_user_cache) > 256:
            expired = [key for key, (expiry, _) in _user_cache.items() if expiry <= now]
            for key in expired:
                _user_cache.pop(key, None)
    return user


def invalidate_token(token: str | None) -> None:
    if not token:
        return
    with _lock:
        _user_cache.pop(token, None)


def _auth_required(configured: bool, available: bool) -> bool:
    flag = settings.xano_auth_required.strip().lower()
    if flag in {"1", "true", "yes", "on"}:
        return True
    if flag in {"0", "false", "no", "off"}:
        return False
    return configured and available


def _auth_endpoints_available() -> bool:
    global _probe
    now = time.monotonic()
    with _lock:
        if _probe and _probe[0] > now:
            return _probe[1]
    available = endpoints_available()
    with _lock:
        _probe = (now + _PROBE_TTL_SECONDS, available)
    return available


class AuthError(XanoAuthError):
    pass
