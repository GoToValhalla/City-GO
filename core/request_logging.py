import json
import logging
import traceback
from collections.abc import Awaitable, Callable
from time import perf_counter
from uuid import uuid4

from core.config import settings
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger("citygo.api.requests")


async def log_request(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    started = perf_counter()
    request_id = request.headers.get("x-request-id") or uuid4().hex
    request.state.request_id = request_id
    try:
        response = await call_next(request)
    except Exception as exc:
        _log(request, 500, started, request_id)
        logger.exception("Unhandled request exception path=%s method=%s", request.url.path, request.method)
        return JSONResponse(
            status_code=500,
            content={
                "error": "unhandled_request_exception",
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "exception_type": exc.__class__.__name__,
                "message": str(exc),
                **_debug_traceback(),
            },
            headers={"X-Request-ID": request_id},
        )
    response.headers["X-Request-ID"] = request_id
    _log(request, response.status_code, started, request_id)
    return response


def _log(request: Request, status_code: int, started: float, request_id: str) -> None:
    payload = {
        "method": request.method,
        "path": request.url.path,
        "request_id": request_id,
        "status_code": status_code,
        "duration_ms": int((perf_counter() - started) * 1000),
    }
    logger.info(json.dumps(payload, sort_keys=True))


def _debug_traceback() -> dict[str, str]:
    return {"traceback": traceback.format_exc()} if settings.app_env != "production" else {}
