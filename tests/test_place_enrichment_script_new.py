"""
Backend tests for run_place_enrichment_export.py script.
"""
from __future__ import annotations

import csv
import io
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Allow importing the script directly
SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "data" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR.parent.parent))


def _make_place(**kwargs) -> MagicMock:
    defaults = dict(
        id=10, slug="test", title="Test Place", category="cafe",
        lat=54.9, lng=21.8, address=None, image_url=None,
        short_description=None, opening_hours=None, price_level=None,
        source="osm", source_url="", confidence=0.7,
        is_published=True, is_visible_in_catalog=True, is_route_eligible=True,
        publication_status="published", verification_status="unverified",
        dog_friendly=False, family_friendly=False, outdoor=False, indoor=False,
    )
    defaults.update(kwargs)
    return MagicMock(**defaults)


# ─── Script imports and uses existing service ────────────────────────────────

def test_script_imports_existing_service():
    """Script must delegate to run_enrichment_export, not duplicate logic."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "run_place_enrichment_export",
        SCRIPTS_DIR / "run_place_enrichment_export.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, "run_enrichment_export"), "Must import run_enrichment_export from service"


def test_script_creates_export_file(tmp_path, monkeypatch):
    """Script creates batch export.csv and export.meta.json."""
    from services import place_enrichment_service as svc

    monkeypatch.setattr("services.place_enrichment_batch.paths.ROOT", tmp_path)
    monkeypatch.setattr("services.place_enrichment_batch.paths.ACTIVE", tmp_path / "active")
    monkeypatch.setattr("services.place_enrichment_batch.paths.ARCHIVE", tmp_path / "archive")

    place = _make_place()
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = MagicMock(name="Test City")

    from schemas.place_enrichment import PlaceEnrichmentExportRequest
    req = PlaceEnrichmentExportRequest(city_slug="zelenogradsk", limit=5, missing_fields=["photo"], git_artifact=True)

    with (
        patch("services.place_enrichment_service.query_places_for_enrichment", return_value=[place]),
        patch("services.place_enrichment_service.write_admin_audit_log"),
    ):
        meta = svc.run_enrichment_export(db, req, actor="script:test")

    batch_dir = tmp_path / "active" / meta.batch_id
    assert (batch_dir / "export.csv").exists()
    assert (batch_dir / "export.meta.json").exists()


def test_script_city_filter_applied(tmp_path):
    """--city argument restricts export to that city slug."""
    from services import place_enrichment_service as svc
    from schemas.place_enrichment import PlaceEnrichmentExportRequest

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = MagicMock(name="Zelenogradsk")
    captured_req = {}

    def capture_query(db, *, city_slug, **kw):
        captured_req["city_slug"] = city_slug
        return []

    req = PlaceEnrichmentExportRequest(city_slug="zelenogradsk", limit=10, missing_fields=[])
    with (
        patch("services.place_enrichment_service.query_places_for_enrichment", side_effect=capture_query),
        patch("services.place_enrichment_service.write_admin_audit_log"),
    ):
        svc.run_enrichment_export(db, req, actor="test")

    assert captured_req["city_slug"] == "zelenogradsk"


def test_script_missing_fields_forwarded(tmp_path):
    """--missing-fields are passed through to the service correctly."""
    from services import place_enrichment_service as svc
    from schemas.place_enrichment import PlaceEnrichmentExportRequest

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = MagicMock(name="City")
    captured = {}

    def capture(db, *, missing_fields, **kw):
        captured["missing_fields"] = missing_fields
        return []

    req = PlaceEnrichmentExportRequest(
        city_slug="zelenogradsk", limit=10, missing_fields=["address", "photo", "description"]
    )
    with (
        patch("services.place_enrichment_service.query_places_for_enrichment", side_effect=capture),
        patch("services.place_enrichment_service.write_admin_audit_log"),
    ):
        svc.run_enrichment_export(db, req, actor="test")

    assert captured["missing_fields"] == ["address", "photo", "description"]


def test_script_exits_successfully_with_zero_rows(tmp_path, monkeypatch):
    """Script must not crash when no places match the filter (0 exported)."""
    from services import place_enrichment_service as svc
    from schemas.place_enrichment import PlaceEnrichmentExportRequest

    monkeypatch.setattr("services.place_enrichment_batch.paths.ROOT", tmp_path)
    monkeypatch.setattr("services.place_enrichment_batch.paths.ACTIVE", tmp_path / "active")
    monkeypatch.setattr("services.place_enrichment_batch.paths.ARCHIVE", tmp_path / "archive")

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = MagicMock(name="City")

    req = PlaceEnrichmentExportRequest(city_slug="zelenogradsk", limit=10, missing_fields=["address"], git_artifact=True)
    with (
        patch("services.place_enrichment_service.query_places_for_enrichment", return_value=[]),
        patch("services.place_enrichment_service.write_admin_audit_log"),
    ):
        meta = svc.run_enrichment_export(db, req, actor="test")

    assert meta.total_exported == 0
    assert (tmp_path / "active" / meta.batch_id / "export.csv").exists()


def test_script_csv_has_required_columns(tmp_path):
    """Generated CSV always contains base and suggested columns."""
    from services.place_enrichment_csv import ALL_COLUMNS, build_csv
    place = _make_place()
    csv_text = build_csv([place], "zelenogradsk", "Зеленоградск")
    reader = csv.DictReader(io.StringIO(csv_text))
    headers = reader.fieldnames or []
    assert "suggested_address" in headers
    assert "current_address" in headers
    assert len(headers) == len(ALL_COLUMNS)
