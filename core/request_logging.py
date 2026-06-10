import json
import logging
from collections.abc import Awaitable, Callable
from time import perf_counter

from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("citygo.api.requests")


async def log_request(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    started = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        _log(request, 500, started)
        raise
    _log(request, response.status_code, started)
    return response


def _log(request: Request, status_code: int, started: float) -> None:
    payload = {
        "method": request.method,
        "path": request.url.path,
        "status_code": status_code,
        "duration_ms": int((perf_counter() - started) * 1000),
    }
    logger.info(json.dumps(payload, sort_keys=True))
