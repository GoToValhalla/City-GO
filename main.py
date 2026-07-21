from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
import logging
import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from starlette.requests import Request
from starlette.responses import Response

from core.abuse_control import AbuseControlMiddleware
from core.admin_background_operation_scheduler import (
    start_admin_background_operation_scheduler,
    stop_admin_background_operation_scheduler,
)
from core.cors import parse_cors_origins
from core.config import settings
from core.import_worker_scheduler import start_import_worker_scheduler, stop_import_worker_scheduler
from core.place_verification_scheduler import start_place_verification_scheduler, stop_place_verification_scheduler
from core.public_access_middleware import public_access_middleware
from core.readiness import check_database_ready
from core.request_logging import log_request
from core.route_state_cleanup_scheduler import start_route_state_cleanup_scheduler, stop_route_state_cleanup_scheduler
from core.router_setup import include_app_routers
from core.safe_errors import install_public_exception_handlers
from core.version import get_backend_version
from db.dependencies import get_db
from services.feature_toggle_service import is_toggle_enabled
from services.user_route_state_integrity import validate_route_state_runtime_config

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    validate_route_state_runtime_config()
    _warn_for_multi_worker_rate_limiting()
    if _is_production():
        missing: list[str] = []
        if not str(settings.admin_api_token or "").strip():
            missing.append("ADMIN_API_TOKEN")
        if not str(settings.user_route_state_secret or "").strip():
            missing.append("USER_ROUTE_STATE_SECRET")
        if missing:
            raise RuntimeError("Missing required production secrets: " + ", ".join(missing))

    start_place_verification_scheduler()
    start_import_worker_scheduler()
    start_route_state_cleanup_scheduler()
    start_admin_background_operation_scheduler()
    try:
        yield
    finally:
        await _stop_schedulers()


async def _stop_schedulers() -> None:
    """Stop every owned scheduler even if an earlier stop raises or is cancelled."""
    try:
        await stop_admin_background_operation_scheduler()
    finally:
        try:
            await stop_route_state_cleanup_scheduler()
        finally:
            try:
                await stop_import_worker_scheduler()
            finally:
                await stop_place_verification_scheduler()


def _is_production() -> bool:
    return str(settings.app_env or "").strip().lower() in {"prod", "production"}


def _warn_for_multi_worker_rate_limiting() -> None:
    raw_workers = os.getenv("WEB_CONCURRENCY", "1")
    try:
        worker_count = int(raw_workers)
    except ValueError:
        worker_count = 1
    if worker_count > 1:
        logger.warning("In-memory rate limits are process-local; WEB_CONCURRENCY=%d weakens aggregate limits", worker_count)


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

install_public_exception_handlers(app)

app.add_middleware(AbuseControlMiddleware)
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
    return JSONResponse(status_code=503, content={"status": "error", "database": reason})


@app.get("/features/public")
def public_features(db: Session = Depends(get_db)) -> dict[str, bool]:
    """Expose only public feature flags required by public clients."""
    return {"tma_enabled": is_toggle_enabled(db, "tma_enabled")}
