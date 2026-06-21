from __future__ import annotations

import importlib
import json
from types import SimpleNamespace
from typing import Any

from core.config import settings


class FakeResponse:
    def __init__(self, payload: bytes, content_type: str = "application/json; charset=utf-8") -> None:
        self._payload = payload
        self.headers = {"Content-Type": content_type}

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._payload


def reset_cache_module(monkeypatch: Any, tmp_path: Any) -> Any:
    import services.local_persistent_cache as local_cache

    if getattr(local_cache, "_CACHE", None) is not None:
        local_cache._CACHE.close()
    monkeypatch.setattr(settings, "local_cache_enabled", True)
    monkeypatch.setattr(settings, "local_cache_dir", str(tmp_path / "diskcache"))
    monkeypatch.setattr(settings, "local_cache_default_ttl_seconds", 3600)
    monkeypatch.setattr(settings, "local_cache_size_limit_bytes", 16 * 1024 * 1024)
    monkeypatch.setattr(settings, "local_cache_shards", 2)
    monkeypatch.setattr(local_cache, "_CACHE", None)
    monkeypatch.setattr(local_cache, "_CACHE_INIT_FAILED", False)
    return local_cache


def test_local_persistent_cache_round_trips_json_and_text_new(monkeypatch: Any, tmp_path: Any) -> None:
    local_cache = reset_cache_module(monkeypatch, tmp_path)

    json_key = local_cache.stable_cache_key("json", {"a": 1})
    text_key = local_cache.stable_cache_key("text", {"b": 2})

    assert local_cache.get_cached_json(json_key) == (False, None)
    local_cache.set_cached_json(json_key, {"ok": True}, tag="test:json")
    assert local_cache.get_cached_json(json_key) == (True, {"ok": True})

    assert local_cache.get_cached_text(text_key) == (False, None)
    local_cache.set_cached_text(text_key, "hello", tag="test:text")
    assert local_cache.get_cached_text(text_key) == (True, "hello")
    assert local_cache.cache_stats()["available"] is True


def test_local_persistent_cache_disabled_is_safe_noop_new(monkeypatch: Any, tmp_path: Any) -> None:
    local_cache = reset_cache_module(monkeypatch, tmp_path)
    monkeypatch.setattr(settings, "local_cache_enabled", False)

    local_cache.set_cached_json("key", {"value": 1})

    assert local_cache.get_cached_json("key") == (False, None)
    assert local_cache.cache_stats() == {"enabled": False, "available": False}


def test_nominatim_reverse_geocode_uses_disk_cache_after_first_fetch_new(monkeypatch: Any, tmp_path: Any) -> None:
    reset_cache_module(monkeypatch, tmp_path)
    import services.place_address_geocode as geocode

    geocode = importlib.reload(geocode)
    calls: list[str] = []
    payload = {"address": {"road": "Main", "house_number": "1", "city": "Test City"}}

    def fake_urlopen(request: Any, timeout: int) -> FakeResponse:
        calls.append(request.full_url)
        return FakeResponse(json.dumps(payload).encode("utf-8"))

    monkeypatch.setattr(geocode.urllib.request, "urlopen", fake_urlopen)

    first = geocode.reverse_geocode_payload(55.123456789, 37.987654321)
    second = geocode.reverse_geocode_payload(55.123456789, 37.987654321)

    assert first == payload
    assert second == payload
    assert len(calls) == 1
    assert geocode.format_nominatim_address(second) == "Main 1, Test City"


def test_image_enrichment_fetch_text_uses_disk_cache_after_first_fetch_new(monkeypatch: Any, tmp_path: Any) -> None:
    reset_cache_module(monkeypatch, tmp_path)
    import data.scripts.enrich_place_images as images

    images = importlib.reload(images)
    calls: list[str] = []

    def fake_urlopen(request: Any, timeout: int) -> FakeResponse:
        calls.append(request.full_url)
        return FakeResponse(b'{"ok": true}', content_type="application/json; charset=utf-8")

    monkeypatch.setattr(images.urllib.request, "urlopen", fake_urlopen)

    first = images._fetch_text("https://example.com/data.json")
    second = images._fetch_text("https://example.com/data.json")

    assert first == '{"ok": true}'
    assert second == '{"ok": true}'
    assert len(calls) == 1


def test_image_enrichment_fetch_text_does_not_cache_provider_failures_new(monkeypatch: Any, tmp_path: Any) -> None:
    reset_cache_module(monkeypatch, tmp_path)
    import data.scripts.enrich_place_images as images

    images = importlib.reload(images)
    calls = SimpleNamespace(count=0)

    def fake_urlopen(request: Any, timeout: int) -> FakeResponse:
        calls.count += 1
        raise TimeoutError("provider timeout")

    monkeypatch.setattr(images.urllib.request, "urlopen", fake_urlopen)

    assert images._fetch_text("https://example.com/timeout") is None
    assert images._fetch_text("https://example.com/timeout") is None
    assert calls.count == 2
