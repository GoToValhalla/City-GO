import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from data.scripts.osm_seed_builder import build_seed, opening_hours, place_from_element
from schemas.place_seed_import_request import PlaceSeedImportRequest
from services.place_coverage_gate_service import evaluate_coverage_gate


def test_place_from_element_maps_osm_to_import_seed_item() -> None:
    element = {
        "type": "node",
        "id": 1,
        "lat": 54.96,
        "lon": 20.48,
        "tags": {"amenity": "cafe", "name": "Кофе", "opening_hours": "09:00-20:00"},
    }

    item = place_from_element(element, datetime(2026, 6, 4, tzinfo=timezone.utc))

    assert item is not None
    assert item["slug"] == "zelenogradsk-coffee-kofe"
    assert item["category"] == "coffee"
    assert item["taxonomy"]["scenario_tags"] == ["coffee_now"]
    assert item["opening_hours"]["mon"] == {"open": "09:00", "close": "20:00"}
    assert item["average_visit_duration_minutes"] == 30


def test_place_from_element_skips_unknown_or_outside_bbox() -> None:
    outside = {"type": "node", "id": 1, "lat": 55.5, "lon": 20.48,
               "tags": {"amenity": "cafe", "name": "Outside"}}
    unknown = {"type": "node", "id": 2, "lat": 54.96, "lon": 20.48,
               "tags": {"amenity": "taxi", "name": "Taxi"}}

    assert place_from_element(outside, datetime(2026, 6, 4, tzinfo=timezone.utc)) is None
    assert place_from_element(unknown, datetime(2026, 6, 4, tzinfo=timezone.utc)) is None


def test_place_from_element_maps_walk_infrastructure() -> None:
    element = {"type": "way", "id": 3, "center": {"lat": 54.961, "lon": 20.472},
               "tags": {"man_made": "pier", "name": "Пирс"}}

    item = place_from_element(element, datetime(2026, 6, 4, tzinfo=timezone.utc))

    assert item is not None
    assert item["category"] == "walk"
    assert item["taxonomy"]["tags"] == ["outdoor", "photo_spot"]


def test_opening_hours_uses_category_default_when_osm_hours_are_missing() -> None:
    hours = opening_hours("", "bar")

    assert hours["mon"] == {"open": "17:00", "close": "01:00"}
    assert set(hours) == {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}


def test_build_seed_from_current_osm_raw_is_import_request_payload() -> None:
    raw = json.loads(Path("data/raw/zelenogradsk_osm.json").read_text())
    payload = build_seed(raw, datetime(2026, 6, 4, tzinfo=timezone.utc))
    request = PlaceSeedImportRequest.model_validate(payload)
    counts = Counter(map(lambda item: item.category, request.items))

    assert request.dry_run is True
    assert len(request.items) >= 80
    assert counts["coffee"] >= 8
    assert counts["food"] >= 8
    assert counts["museum"] >= 1
    assert counts["bar"] >= 1
    assert counts["park"] >= 1


def test_current_osm_plus_editorial_seed_passes_release_coverage_shape() -> None:
    paths = (
        Path("data/seeds/place_import/zelenogradsk_osm.json"),
        Path("data/seeds/place_import/zelenogradsk_editorial_walks.json"),
    )
    requests = tuple(map(lambda path: PlaceSeedImportRequest.model_validate(json.loads(path.read_text())), paths))
    items = [item for request in requests for item in request.items]
    counts = Counter(map(lambda item: item.category, items))
    report = {
        "total_places": len(items),
        "with_coordinates": sum(map(lambda item: int(item.lat is not None and item.lng is not None), items)),
        "with_opening_hours": sum(map(lambda item: int(bool(item.opening_hours)), items)),
        "with_visit_duration": sum(map(lambda item: int(item.average_visit_duration_minutes is not None), items)),
        "category_counts": dict(counts),
    }

    result = evaluate_coverage_gate(report)

    assert result.passed is True
