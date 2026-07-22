"""Stable public HTTP failure contract for projection reads."""

from typing import NoReturn

from fastapi import HTTPException

from services.public_read_projection_service import PublicReadProjectionError
from services.projection_observability import log_projection_unavailable


def raise_projection_unavailable(exc: PublicReadProjectionError, *, read_path: str) -> NoReturn:
    log_projection_unavailable(read_path=read_path, reason=exc.reason)
    raise HTTPException(
        status_code=503,
        detail={
            "code": "public_read_projection_unavailable",
            "reason": exc.reason,
            "read_path": read_path,
            "message": str(exc),
        },
    ) from exc
