from __future__ import annotations

import json
from unittest.mock import patch

from core.config import settings
from services.geocoding_service import GeocodingService


class _FakeResponse:
    """Минимальный context manager для urllib.urlopen в тесте."""

    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


def test_geocode_new_returns_point_from_geoapify(monkeypatch) -> None:
    monkeypatch.setattr(settings, "geoapify_api_key", "key")
    payload = {"features": [{"properties": {"lat": 61.0, "lon": 69.0, "formatted": "Адрес"}}]}

    with patch("urllib.request.urlopen", return_value=_FakeResponse(payload)):
        point = GeocodingService().geocode("Мира 1", "Ханты-Мансийск")

    assert point is not None
    assert point.lat == 61.0
    assert point.lng == 69.0
    assert point.formatted_address == "Адрес"


def test_geocode_new_returns_none_without_key(monkeypatch) -> None:
    monkeypatch.setattr(settings, "geoapify_api_key", "")

    point = GeocodingService().geocode("Мира 1", "Ханты-Мансийск")

    assert point is None
