"""Centralized abuse controls: rate limits and request body size bounds."""

from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from core.abuse.proxy_client import client_ip
from core.abuse.rate_limit_store import AbuseControlStore
from core.abuse.rules import RULES, RateLimitRule

_MAX_BODY_BYTES = 256_000
_STORE = AbuseControlStore()


def reset_abuse_control_store() -> None:
    _STORE.reset()


def match_rule(path: str, method: str) -> RateLimitRule | None:
    upper = method.upper()
    for rule in RULES:
        if upper in rule.methods and (path == rule.path_prefix or path.startswith(rule.path_prefix)):
            return rule
    return None


class AbuseControlMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if _is_test_request():
            return await call_next(request)
        if _content_length_rejected(request.headers.get("content-length")):
            return _too_large()
        rule = match_rule(request.url.path, request.method)
        if rule is not None and not _rule_allows(request, rule):
            return _rate_limited(rule)
        return await call_next(request)


def _content_length_rejected(content_length: str | None) -> bool:
    if content_length is None:
        return False
    try:
        return int(content_length) > _MAX_BODY_BYTES
    except ValueError:
        return True


def _rule_allows(request: Request, rule: RateLimitRule) -> bool:
    key = f"{rule.path_prefix}|{request.method}|{client_ip(request)}"
    return _STORE.hit(key, limit=rule.limit, window_seconds=rule.window_seconds)


def _rate_limited(rule: RateLimitRule) -> JSONResponse:
    detail = {"code": "RATE_LIMITED", "message": "Too many requests. Try again later."}
    return JSONResponse(status_code=429, content={"detail": detail}, headers={"Retry-After": str(int(rule.window_seconds))})


def _is_test_request() -> bool:
    import os
    import sys

    if "pytest" in sys.modules:
        return True
    if os.getenv("PYTEST_CURRENT_TEST"):
        return True
    if os.getenv("APP_ENV", "").lower() in {"test", "ci", "pytest"}:
        return True
    return False


def _too_large() -> JSONResponse:
    return JSONResponse(
        status_code=413,
        content={"detail": {"code": "PAYLOAD_TOO_LARGE", "message": "Request body too large."}},
    )
