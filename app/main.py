from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.auth import auth_is_required, bearer_token, resolve_user
from app.core.config import settings
from app.services.store import store
from app.services.xano_auth import XanoAuthError

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_prefix)

_PUBLIC_PATHS = {
    "/",
    "/api/health",
    "/api/auth/status",
    "/api/auth/signup",
    "/api/auth/login",
    "/api/auth/logout",
    "/api/auth/me",
    "/api/integrations/linkedin/callback",
}


@app.middleware("http")
async def xano_auth_middleware(request: Request, call_next):
    if request.method == "OPTIONS" or _is_public(request.url.path):
        return await call_next(request)

    token = bearer_token(request)
    if token:
        try:
            user = resolve_user(token)
        except XanoAuthError as exc:
            if auth_is_required():
                return JSONResponse({"detail": str(exc)}, status_code=exc.status_code)
            return await call_next(request)
        request.state.user = user
        store.bind_identity(user.id, email=user.email, full_name=user.name)
        return await call_next(request)

    if auth_is_required() and request.url.path.startswith("/api/"):
        return JSONResponse({"detail": "Authentication required."}, status_code=401)
    return await call_next(request)


def _is_public(path: str) -> bool:
    if path in _PUBLIC_PATHS:
        return True
    if path.startswith("/api/internal"):
        return True
    return path.startswith("/docs") or path.startswith("/redoc") or path == "/openapi.json"


@app.get("/")
def root() -> dict[str, str]:
    return {"service": settings.app_name, "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.port, reload=True)
