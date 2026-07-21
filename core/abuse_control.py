"""Centralized abuse controls: rate limits and request body size bounds."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from core.abuse.proxy_client import client_ip
from core.abuse.rate_limit_store import AbuseControlStore
from core.abuse.rules import RULES, RateLimitRule

_MAX_BODY_BYTES = 256_000
_STORE = AbuseControlStore()


def reset_abuse_control_store() -> None:
    _STORE.reset()


def _path_matches(path: str, prefix: str) -> bool:
    normalized = prefix.rstrip("/") or "/"
    return path == normalized or path.startswith(normalized + "/")


def match_rule(path: str, method: str) -> RateLimitRule | None:
    upper = method.upper()
    for rule in RULES:
        if upper in rule.methods and _path_matches(path, rule.path_prefix):
            return rule
    return None


class AbuseControlMiddleware:
    """ASGI middleware that enforces limits on the bytes actually received."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope)
        if _content_length_rejected(request.headers.get("content-length")):
            await _too_large()(scope, receive, send)
            return

        rule = match_rule(request.url.path, request.method)
        if rule is not None and not _rule_allows(request, rule):
            await _rate_limited(rule)(scope, receive, send)
            return

        buffered: list[Message] = []
        total = 0
        more_body = True
        while more_body:
            message = await receive()
            if message["type"] != "http.request":
                buffered.append(message)
                break
            total += len(message.get("body", b""))
            if total > _MAX_BODY_BYTES:
                await _too_large()(scope, _empty_receive, send)
                return
            buffered.append(message)
            more_body = bool(message.get("more_body", False))

        index = 0

        async def replay_receive() -> Message:
            nonlocal index
            if index < len(buffered):
                message = buffered[index]
                index += 1
                return message
            return await receive()

        await self.app(scope, replay_receive, send)


def _content_length_rejected(content_length: str | None) -> bool:
    if content_length is None:
        return False
    try:
        return int(content_length) > _MAX_BODY_BYTES
    except ValueError:
        return True


def _rule_allows(request: Request, rule: RateLimitRule) -> bool:
    key = f"{rule.key}|{request.method.upper()}|{client_ip(request)}"
    return _STORE.hit(key, limit=rule.limit, window_seconds=rule.window_seconds)


def _rate_limited(rule: RateLimitRule) -> JSONResponse:
    detail = {"code": "RATE_LIMITED", "message": "Too many requests. Try again later."}
    return JSONResponse(status_code=429, content={"detail": detail}, headers={"Retry-After": str(int(rule.window_seconds))})


def _too_large() -> JSONResponse:
    return JSONResponse(
        status_code=413,
        content={"detail": {"code": "PAYLOAD_TOO_LARGE", "message": "Request body too large."}},
    )


async def _empty_receive() -> Message:
    return {"type": "http.request", "body": b"", "more_body": False}
