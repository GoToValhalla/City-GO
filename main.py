from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.requests import Request
from starlette.responses import Response

from core.cors import parse_cors_origins
from core.config import settings
from core.import_worker_scheduler import (
    start_import_worker_scheduler,
    stop_import_worker_scheduler,
)
from core.place_verification_scheduler import (
    start_place_verification_scheduler,
    stop_place_verification_scheduler,
)
from core.readiness import check_database_ready
from core.request_logging import log_request
from core.public_access_middleware import public_access_middleware
from core.router_setup import include_app_routers
from core.version import get_backend_version


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Fail-fast: в production admin token обязателен.
    if settings.app_env == "production" and not settings.admin_api_token:
        raise RuntimeError(
            "ADMIN_API_TOKEN must be set in production. "
            "Set it via environment variable before starting the app."
        )
    start_place_verification_scheduler()
    start_import_worker_scheduler()
    try:
        yield
    finally:
        await stop_import_worker_scheduler()
        await stop_place_verification_scheduler()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=parse_cors_origins(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def maintenance_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    return await public_access_middleware(request, call_next)


@app.middleware("http")
async def request_logging_middleware(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    return await log_request(request, call_next)


include_app_routers(app)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/version")
def version() -> dict[str, str]:
    return get_backend_version()


@app.get("/ready", response_model=None)
def ready() -> JSONResponse | dict[str, str]:
    db_ready, reason = check_database_ready()
    if db_ready:
        return {"status": "ok", "database": "ok"}
    return JSONResponse(
        status_code=503,
        content={"status": "error", "database": reason},
    )
