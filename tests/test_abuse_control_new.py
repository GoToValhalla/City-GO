"""AbuseControlMiddleware rate limits and payload size."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from core import abuse_control
from core.abuse_control import AbuseControlMiddleware, reset_abuse_control_store
from core.abuse.proxy_client import client_ip
from core.abuse.rate_limit_store import AbuseControlStore
from starlette.requests import Request
from fastapi.routing import APIRoute
from core.admin_auth import admin_required
from main import app as production_app
from main import _warn_for_multi_worker_rate_limiting
from concurrent.futures import ThreadPoolExecutor


def test_abuse_control_rate_limits_and_payload_new(monkeypatch) -> None:
    reset_abuse_control_store()
    monkeypatch.setattr(abuse_control, "_is_test_request", lambda: False)
    app = FastAPI()
    app.add_middleware(AbuseControlMiddleware)

    @app.post("/routes/random")
    def random_route() -> dict[str, str]:
        return {"ok": "1"}

    client = TestClient(app)
    too_large = client.post("/routes/random", headers={"content-length": "999999"}, content=b"x")
    assert too_large.status_code == 413

    statuses = [client.post("/routes/random", json={}).status_code for _ in range(35)]
    assert 429 in statuses
    assert statuses.count(200) <= 30


def _request(client: str, forwarded: str | None = None) -> Request:
    headers = [] if forwarded is None else [(b"x-forwarded-for", forwarded.encode())]
    return Request({"type": "http", "client": (client, 1234), "headers": headers})


def test_forged_forwarded_for_is_ignored_new() -> None:
    assert client_ip(_request("203.0.113.8", "198.51.100.4")) == "203.0.113.8"


def test_forwarded_for_from_trusted_proxy_is_used_new() -> None:
    assert client_ip(_request("127.0.0.1", "198.51.100.4")) == "198.51.100.4"


def test_rate_limit_store_is_bounded_and_expires_new(monkeypatch) -> None:
    clock = iter((0.0, 0.0, 0.0, 2.0))
    monkeypatch.setattr("core.abuse.rate_limit_store.time.monotonic", lambda: next(clock))
    store = AbuseControlStore(max_keys=2)
    assert store.hit("a", limit=1, window_seconds=1.0)
    assert store.hit("b", limit=1, window_seconds=1.0)
    assert store.hit("c", limit=1, window_seconds=1.0)
    assert store.key_count == 2
    assert store.hit("b", limit=1, window_seconds=1.0)


def _depends_on(dependant, target) -> bool:
    return dependant.call is target or any(_depends_on(child, target) for child in dependant.dependencies)


def test_every_active_public_write_has_rate_limit_new() -> None:
    missing = []
    for route in production_app.routes:
        if not isinstance(route, APIRoute) or _depends_on(route.dependant, admin_required):
            continue
        for method in set(route.methods or ()) & {"POST", "PUT", "PATCH", "DELETE"}:
            if abuse_control.match_rule(route.path, method) is None:
                missing.append(f"{method}:{route.path}")
    assert missing == []


def test_rate_limit_store_serializes_concurrent_hits_new() -> None:
    store = AbuseControlStore(max_keys=10)
    with ThreadPoolExecutor(max_workers=16) as pool:
        allowed = list(pool.map(lambda _: store.hit("same", limit=20, window_seconds=60), range(100)))
    assert sum(allowed) == 20


def test_recommendation_aliases_have_equal_limits_new() -> None:
    canonical = abuse_control.match_rule("/recommendations/route", "POST")
    alias = abuse_control.match_rule("/v1/recommendations/route", "POST")
    assert canonical is not None and alias is not None
    assert (canonical.limit, canonical.window_seconds) == (alias.limit, alias.window_seconds)


def test_multi_worker_configuration_emits_warning_new(monkeypatch, caplog) -> None:
    monkeypatch.setenv("WEB_CONCURRENCY", "2")
    _warn_for_multi_worker_rate_limiting()
    assert "process-local" in caplog.text
