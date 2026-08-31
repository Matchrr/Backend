from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from app.core.auth import auth_status, bearer_token, invalidate_token, resolve_user
from app.core.config import settings
from app.services import google_auth
from app.services.store import store
from app.services.xano_auth import (
    XanoAuthError,
    login,
    login_with_google,
    request_password_reset,
    reset_password,
    signup,
    user_to_dict,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=256)


class SessionResponse(BaseModel):
    token: str
    user: dict


class ForgotPasswordRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)


class ResetPasswordRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    token: str = Field(min_length=8, max_length=512)
    password: str = Field(min_length=8, max_length=256)


@router.get("/status")
def get_auth_status() -> dict:
    return auth_status()


@router.get("/google/authorize")
def google_authorize() -> dict[str, object]:
    if not google_auth.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Google sign-in is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
        )
    try:
        return {"url": google_auth.build_authorization_url(), "configured": True}
    except google_auth.GoogleAuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/google/callback")
def google_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
) -> RedirectResponse:
    frontend = settings.frontend_url.rstrip("/")
    if error:
        return _google_redirect(frontend, error=error_description or error)
    try:
        profile = google_auth.complete_login(code, state)
        token, user = login_with_google(
            profile["email"],
            profile["name"],
            profile["google_id"],
            google_auth.random_account_password(),
        )
    except google_auth.GoogleAuthError as exc:
        return _google_redirect(frontend, error=str(exc))
    except XanoAuthError as exc:
        return _google_redirect(frontend, error=str(exc))
    store.bind_identity(user.id, email=user.email, full_name=user.name)
    return _google_redirect(frontend, token=token)


def _google_redirect(frontend: str, *, token: str | None = None, error: str | None = None) -> RedirectResponse:
    query: dict[str, str] = {}
    if token:
        query["token"] = token
    if error:
        query["error"] = error[:180]
    return RedirectResponse(f"{frontend}/auth/google/callback?{urlencode(query)}", status_code=302)


@router.post("/signup", response_model=SessionResponse)
def signup_user(payload: Credentials) -> SessionResponse:
    try:
        token, user = signup(payload.email.strip().lower(), payload.password)
    except XanoAuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    store.bind_identity(user.id, email=user.email, full_name=user.name)
    return SessionResponse(token=token, user=user_to_dict(user))


@router.post("/login", response_model=SessionResponse)
def login_user(payload: Credentials) -> SessionResponse:
    try:
        token, user = login(payload.email.strip().lower(), payload.password)
    except XanoAuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    store.bind_identity(user.id, email=user.email, full_name=user.name)
    return SessionResponse(token=token, user=user_to_dict(user))


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest) -> dict[str, str]:
    email = payload.email.strip().lower()
    try:
        request_password_reset(email, origin=settings.frontend_url)
    except XanoAuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return {"status": "ok"}


@router.post("/reset-password", response_model=SessionResponse)
def reset_password_user(payload: ResetPasswordRequest) -> SessionResponse:
    try:
        token, user = reset_password(
            payload.email.strip().lower(),
            payload.token.strip(),
            payload.password,
        )
    except XanoAuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    store.bind_identity(user.id, email=user.email, full_name=user.name)
    return SessionResponse(token=token, user=user_to_dict(user))


@router.get("/me")
def current_user(request: Request) -> dict:
    token = bearer_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required.")
    try:
        user = resolve_user(token)
    except XanoAuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    store.bind_identity(user.id, email=user.email, full_name=user.name)
    return user_to_dict(user)


@router.post("/logout")
def logout_user(request: Request) -> dict[str, str]:
    invalidate_token(bearer_token(request))
    return {"status": "ok"}
