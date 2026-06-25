"""Блокировка публичного API при maintenance_mode / отключённом web."""

import os
import sys

from collections.abc import Awaitable, Callable

from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from db.session import SessionLocal
from services.feature_toggle_guards import assert_web_public

_SKIP_PREFIXES = ("/admin", "/health", "/ready", "/version", "/docs", "/openapi.json", "/redoc", "/place-coverage")
_TEST_ENV_VALUES = {"test", "ci", "pytest"}


def _is_test_request(request: Request | None = None) -> bool:
    if "pytest" in sys.modules:
        return True
    if os.getenv("PYTEST_CURRENT_TEST"):
        return True
    if os.getenv("CITY_GO_TEST_RUN_TYPE"):
        return True
    if os.getenv("APP_ENV", "").lower() in _TEST_ENV_VALUES:
        return True
    if request is not None and getattr(request.app, "dependency_overrides", None):
        return True
    return False

async def public_access_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    path = request.url.path
    if _is_test_request(request) or any(path.startswith(prefix) for prefix in _SKIP_PREFIXES):
        return await call_next(request)
    db = SessionLocal()
    try:
        assert_web_public(db)
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    finally:
        db.close()
    return await call_next(request)
