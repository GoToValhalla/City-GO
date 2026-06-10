"""
Backend tests for place_enrichment endpoints and service logic.
"""
from __future__ import annotations

import csv
import io
import json
from unittest.mock import MagicMock, patch

import pytest

from schemas.place_enrichment import PlaceEnrichmentExportRequest
from services.place_enrichment_csv import ALL_COLUMNS, BASE_COLUMNS, SUGGESTED_COLUMNS, build_csv
from services.place_enrichment_query import missing_fields_breakdown, query_places_for_enrichment


def _make_place(**kwargs) -> MagicMock:
    defaults = dict(
        id=1, slug="test-place", title="Test", category="cafe",
        lat=54.9, lng=21.8, address=None, image_url=None,
        short_description=None, opening_hours=None, price_level=None,
        source="osm", source_url="https://osm.org/1", confidence=0.7,
        is_published=True, is_visible_in_catalog=True, is_route_eligible=True,
        publication_status="published", verification_status="unverified",
        dog_friendly=False, family_friendly=False, outdoor=False, indoor=False,
    )
    defaults.update(kwargs)
    return MagicMock(**defaults)


# ─── CSV structure ────────────────────────────────────────────────────────────

def test_csv_contains_all_base_columns():
    place = _make_place()
    csv_text = build_csv([place], "zelenogradsk", "Зеленоградск")
    reader = csv.DictReader(io.StringIO(csv_text))
    headers = reader.fieldnames or []
    for col in BASE_COLUMNS:
        assert col in headers, f"Missing base column: {col}"


def test_csv_contains_suggested_columns():
    place = _make_place()
    csv_text = build_csv([place], "zelenogradsk", "Зеленоградск")
    reader = csv.DictReader(io.StringIO(csv_text))
    headers = reader.fieldnames or []
    for col in SUGGESTED_COLUMNS:
        assert col in headers, f"Missing suggested column: {col}"


def test_csv_suggested_columns_are_empty_on_export():
    place = _make_place(address="ул. Ленина 1")
    csv_text = build_csv([place], "zelenogradsk", "Зеленоградск")
    reader = csv.DictReader(io.StringIO(csv_text))
    rows = list(reader)
    assert len(rows) == 1
    for col in SUGGESTED_COLUMNS:
        assert rows[0][col] == "", f"Suggested column should be empty: {col}"


def test_csv_current_address_populated():
    place = _make_place(address="ул. Ленина 5")
    csv_text = build_csv([place], "zelenogradsk", "Зеленоградск")
    rows = list(csv.DictReader(io.StringIO(csv_text)))
    assert rows[0]["current_address"] == "ул. Ленина 5"


# ─── Missing field filters ────────────────────────────────────────────────────

def test_filter_missing_address_excludes_places_with_address():
    places = [_make_place(address="ул. 1"), _make_place(id=2, slug="b", address=None)]
    result = [p for p in places if not (p.address or "").strip()]
    assert len(result) == 1
    assert result[0].id == 2


def test_filter_missing_photo_excludes_places_with_photo():
    places = [_make_place(image_url="http://img.jpg"), _make_place(id=2, slug="b", image_url=None)]
    result = [p for p in places if not p.image_url]
    assert len(result) == 1
    assert result[0].id == 2


def test_filter_missing_menu_url_always_true():
    """menu_url is not in Place model — always counts as missing."""
    from services.place_enrichment_query import _MISSING_CHECKS
    place = _make_place()
    assert _MISSING_CHECKS["menu_url"](place) is True


def test_missing_fields_breakdown_counts_correctly():
    place_no_addr = _make_place(address=None, image_url="http://img.jpg")
    place_no_photo = _make_place(id=2, slug="b", address="ул. 1", image_url=None)
    breakdown = missing_fields_breakdown([place_no_addr, place_no_photo], ["address", "photo"])
    assert breakdown["address"] == 1
    assert breakdown["photo"] == 1


# ─── Service integration (mocked DB) ─────────────────────────────────────────

def test_run_enrichment_export_creates_files(tmp_path, monkeypatch):
    from services import place_enrichment_service as svc

    monkeypatch.setattr("services.place_enrichment_batch.paths.ROOT", tmp_path)
    monkeypatch.setattr("services.place_enrichment_batch.paths.ACTIVE", tmp_path / "active")
    monkeypatch.setattr("services.place_enrichment_batch.paths.ARCHIVE", tmp_path / "archive")

    place = _make_place()
    db = MagicMock()
    city_mock = MagicMock()
    city_mock.name = "Зеленоградск"
    db.query.return_value.filter.return_value.first.return_value = city_mock

    req = PlaceEnrichmentExportRequest(city_slug="zelenogradsk", limit=10, missing_fields=["address"], git_artifact=True)

    with (
        patch("services.place_enrichment_service.query_places_for_enrichment", return_value=[place]),
        patch("services.place_enrichment_service.write_admin_audit_log"),
    ):
        meta = svc.run_enrichment_export(db, req, actor="admin")

    batch_dir = tmp_path / "active" / meta.batch_id
    assert meta.total_exported == 1
    assert (batch_dir / "export.csv").exists()
    assert (batch_dir / "export.meta.json").exists()


def test_run_enrichment_export_writes_audit_log(tmp_path, monkeypatch):
    from services import place_enrichment_service as svc

    monkeypatch.setattr("services.place_enrichment_batch.paths.ROOT", tmp_path)
    monkeypatch.setattr("services.place_enrichment_batch.paths.ACTIVE", tmp_path / "active")
    monkeypatch.setattr("services.place_enrichment_batch.paths.ARCHIVE", tmp_path / "archive")

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = MagicMock(name="Зеленоградск")
    req = PlaceEnrichmentExportRequest(city_slug="zelenogradsk", limit=10, missing_fields=[], git_artifact=True)

    with (
        patch("services.place_enrichment_service.query_places_for_enrichment", return_value=[]),
        patch("services.place_enrichment_service.write_admin_audit_log") as mock_audit,
    ):
        svc.run_enrichment_export(db, req, actor="test-admin")

    mock_audit.assert_called_once()
    call_kwargs = mock_audit.call_args.kwargs
    assert call_kwargs["action"] == "place_enrichment_export"
    assert call_kwargs["entity_type"] == "place_enrichment_batch"
    assert call_kwargs["actor"] == "test-admin"
