from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.auth import auth_status, bearer_token, invalidate_token, resolve_user
from app.services.store import store
from app.services.xano_auth import XanoAuthError, login, signup, user_to_dict

router = APIRouter(prefix="/auth", tags=["auth"])


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=256)


class SessionResponse(BaseModel):
    token: str
    user: dict


@router.get("/status")
def get_auth_status() -> dict:
    return auth_status()


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
