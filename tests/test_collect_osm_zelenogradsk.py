import json
from datetime import datetime, timezone
from pathlib import Path

from data.scripts.collect_osm_zelenogradsk import collect_places, overpass_query


class _Response:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_overpass_query_collects_route_relevant_tags() -> None:
    query = overpass_query()

    assert 'nwr["amenity"~"cafe|restaurant|bar|pub|fast_food|ice_cream|marketplace"]' in query
    assert 'nwr["leisure"~"park|garden|playground|fitness_station|sports_centre"]' in query
    assert 'nwr["natural"~"beach"]' in query
    assert 'nwr["man_made"~"pier|tower"]' in query
    assert 'nwr["highway"~"pedestrian|footway"]["name"]' in query


def test_collect_places_writes_raw_and_seed_payload(tmp_path) -> None:
    raw_payload = {
        "elements": [
            {"type": "node", "id": 1, "lat": 54.96, "lon": 20.48,
             "tags": {"amenity": "cafe", "name": "Кофе"}},
            {"type": "way", "id": 2, "center": {"lat": 54.961, "lon": 20.472},
             "tags": {"man_made": "pier", "name": "Пирс"}},
        ]
    }

    def opener(url: str, data: bytes, timeout: int) -> _Response:
        assert "overpass" in url
        assert b"data=" in data
        assert timeout == 90
        return _Response(raw_payload)

    result = collect_places(
        raw_path=tmp_path / "raw.json",
        seed_path=tmp_path / "seed.json",
        opener=opener,
        now=datetime(2026, 6, 4, tzinfo=timezone.utc),
    )
    seed = json.loads((tmp_path / "seed.json").read_text())

    assert result == {"raw_elements": 2, "seed_items": 2}
    assert seed["items"][0]["category"] == "coffee"
    assert seed["items"][1]["category"] == "walk"
    assert json.loads((tmp_path / "raw.json").read_text()) == raw_payload


def test_legacy_fetch_script_uses_collector_without_requests_dependency() -> None:
    source = Path("data/scripts/fetch_osm_zelenogradsk.py").read_text()

    assert "collect_osm_zelenogradsk" in source
    assert "import requests" not in source
