"""Блокировка публичного API при maintenance_mode / отключённом web."""

from collections.abc import Awaitable, Callable

from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from db.session import SessionLocal
from services.feature_toggle_guards import assert_web_public

_SKIP_PREFIXES = ("/admin", "/health", "/ready", "/version", "/docs", "/openapi.json", "/redoc", "/place-coverage")


async def public_access_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    path = request.url.path
    if any(path.startswith(prefix) for prefix in _SKIP_PREFIXES):
        return await call_next(request)
    db = SessionLocal()
    try:
        assert_web_public(db)
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    finally:
        db.close()
    return await call_next(request)
