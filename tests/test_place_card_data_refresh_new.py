from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from services.place_data_merge_service import PlaceDataMergeService
from services.place_data_sanitizer import category_payload, clean_text
from services.place_lineage import LineageEntry, validate_lineage_map


def test_lineage_validator_accepts_strict_schema_new() -> None:
    entry = LineageEntry(source="MANUAL", updated_at=datetime.now(timezone.utc), confidence=1.0, priority=100)
    assert validate_lineage_map({"title": entry.model_dump()})["title"]["priority"] == 100


def test_lineage_validator_rejects_broken_schema_on_write_new() -> None:
    with pytest.raises(ValueError):
        validate_lineage_map({"title": {"source": "MANUAL", "updated_at": "2026-01-01T00:00:00", "confidence": 2, "priority": 100}})


def test_data_sanitizer_removes_raw_codes_new() -> None:
    assert clean_text("amenity:cafe") is None
    assert clean_text("undefined") is None
    assert category_payload("museum")["label"] == "Музей"


def test_public_place_detail_no_internal_fields_new(client, city_factory, published_place_factory) -> None:
    city = city_factory(slug="clean-public-city")
    place = published_place_factory(city_id=city.id, category="museum", title="Музей", address="ул. 1")
    response = client.get(f"/places/{place.id}")
    raw = json.dumps(response.json(), ensure_ascii=False).lower()
    assert response.status_code == 200
    assert "source_url" not in raw
    assert "confidence" not in raw
    assert "verification_" not in raw
    assert response.json()["category_label"] == "Музей"


def test_public_place_detail_degraded_fallback_new(client, city_factory, published_place_factory) -> None:
    city = city_factory(slug="degraded-public-city")
    place = published_place_factory(city_id=city.id, category="park", title="Парк", address=None)
    place.completeness_score = 0
    response = client.get(f"/places/{place.id}")
    assert response.status_code == 200
    assert response.json()["data_quality"]["is_degraded"] is True


def test_service_only_place_hidden_from_public_catalog_new(client, db_session, city_factory, published_place_factory) -> None:
    city = city_factory(slug="service-only-city")
    place = published_place_factory(city_id=city.id, category="museum", title="Аптека в парке")
    place.canonical_category = None
    db_session.commit()
    PlaceDataMergeService().apply_safe(db_session, place.id, {"canonical_category": "pharmacy"}, "MANUAL", 1.0, "test")
    assert client.get(f"/places/{place.id}").status_code == 404
    assert client.get(f"/places/?city_slug={city.slug}").json()["total"] == 0
