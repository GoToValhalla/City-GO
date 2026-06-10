"""Tests for GitHub-based place enrichment batch workflow."""
from __future__ import annotations

import csv
import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from schemas.place_enrichment import PlaceEnrichmentExportRequest
from services.place_enrichment_batch.meta import read_batch_meta
from services.place_enrichment_batch.paths import ACTIVE, make_batch_id
from services.place_enrichment_import.preview_builder import build_preview
from services.place_enrichment_import_service import run_import_apply, run_import_preview
from services.place_enrichment_service import run_enrichment_export


def _place(**kw) -> MagicMock:
    d = dict(
        id=1, slug="test-place", title="Test", category="cafe",
        address=None, short_description="old", price_level=None,
        dog_friendly=False, family_friendly=False, outdoor=False, indoor=False,
        opening_hours=None, image_url=None, lat=54.9, lng=21.8,
        source="osm", source_url="", confidence=0.7,
        is_published=True, is_visible_in_catalog=True, is_route_eligible=True,
        publication_status="published", verification_status="unverified",
    )
    d.update(kw)
    return MagicMock(**d)


@pytest.fixture()
def batch_root(tmp_path, monkeypatch):
    monkeypatch.setattr("services.place_enrichment_batch.paths.ROOT", tmp_path)
    monkeypatch.setattr("services.place_enrichment_batch.paths.ACTIVE", tmp_path / "active")
    monkeypatch.setattr("services.place_enrichment_batch.paths.ARCHIVE", tmp_path / "archive")
    monkeypatch.setattr("services.place_enrichment_service.ROOT", tmp_path)
    return tmp_path


def test_git_artifact_creates_active_batch(batch_root):
    place = _place()
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = MagicMock(name="Zelenogradsk")
    req = PlaceEnrichmentExportRequest(city_slug="zelenogradsk", limit=10, missing_fields=["photo"], git_artifact=True)
    with (
        patch("services.place_enrichment_service.query_places_for_enrichment", return_value=[place]),
        patch("services.place_enrichment_service.write_admin_audit_log"),
    ):
        meta = run_enrichment_export(db, req, actor="test")
    batch_dir = batch_root / "active" / meta.batch_id
    assert (batch_dir / "export.csv").exists()
    assert (batch_dir / "export.meta.json").exists()
    assert not (batch_dir / "enriched.csv").exists()


def test_meta_contains_correct_paths(batch_root):
    place = _place()
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = MagicMock(name="City")
    req = PlaceEnrichmentExportRequest(city_slug="zelenogradsk", limit=5, git_artifact=True)
    with (
        patch("services.place_enrichment_service.query_places_for_enrichment", return_value=[place]),
        patch("services.place_enrichment_service.write_admin_audit_log"),
    ):
        meta = run_enrichment_export(db, req, actor="test")
    saved = read_batch_meta(meta.batch_id)
    assert saved is not None
    assert saved.export_csv_path.endswith("/export.csv")
    assert saved.status == "exported"
    assert saved.next_action == "chatgpt_enrich"


def test_preview_fails_without_enriched(batch_root):
    bid = make_batch_id("zelenogradsk")
    root = batch_root / "active" / bid
    root.mkdir(parents=True)
    (root / "export.csv").write_text("id,slug\n1,a\n", encoding="utf-8")
    from services.place_enrichment_batch.meta import build_batch_meta, write_batch_meta
    write_batch_meta(build_batch_meta(
        batch_id=bid, city_slug="zelenogradsk", limit=10, missing_fields=[],
        only_published=True, only_route_eligible=False, total_exported=0,
        by_city={}, by_category={}, breakdown={},
    ))
    db = MagicMock()
    with pytest.raises(FileNotFoundError, match="enriched.csv"):
        run_import_preview(db, bid)


def test_preview_detects_address_change(batch_root):
    bid = make_batch_id("zelenogradsk")
    root = batch_root / "active" / bid
    root.mkdir(parents=True)
    from services.place_enrichment_batch.meta import build_batch_meta, write_batch_meta
    write_batch_meta(build_batch_meta(
        batch_id=bid, city_slug="zelenogradsk", limit=10, missing_fields=[],
        only_published=True, only_route_eligible=False, total_exported=1,
        by_city={"zelenogradsk": 1}, by_category={}, breakdown={},
    ))
    header = "id,slug,title,suggested_address,suggested_image_url,suggested_website"
    (root / "export.csv").write_text(f"{header}\n1,test-place,Test,,,\n", encoding="utf-8")
    (root / "enriched.csv").write_text(
        f"{header}\n1,test-place,Test,Московская 68,http://img.jpg,http://site.com\n",
        encoding="utf-8",
    )
    place = _place(address=None)
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = [place]
    preview = run_import_preview(db, bid)
    assert preview.rows_with_changes == 1
    assert preview.changes[0].updates[0].field == "address"
    assert preview.unsupported_fields.get("suggested_image_url") == 1
    assert (root / "import.preview.json").exists()


def test_preview_does_not_modify_db(batch_root):
    bid = make_batch_id("z")
    root = batch_root / "active" / bid
    root.mkdir(parents=True)
    from services.place_enrichment_batch.meta import build_batch_meta, write_batch_meta
    write_batch_meta(build_batch_meta(
        batch_id=bid, city_slug="z", limit=1, missing_fields=[],
        only_published=True, only_route_eligible=False, total_exported=1,
        by_city={"z": 1}, by_category={}, breakdown={},
    ))
    (root / "export.csv").write_text("id,slug,title,suggested_address\n1,p,T,old\n", encoding="utf-8")
    (root / "enriched.csv").write_text("id,slug,title,suggested_address\n1,p,T,new addr\n", encoding="utf-8")
    place = _place(address="old")
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = [place]
    run_import_preview(db, bid)
    assert place.address == "old"


def test_apply_updates_allowed_fields(batch_root):
    bid = make_batch_id("z")
    root = batch_root / "active" / bid
    root.mkdir(parents=True)
    from services.place_enrichment_batch.meta import build_batch_meta, write_batch_meta
    write_batch_meta(build_batch_meta(
        batch_id=bid, city_slug="z", limit=1, missing_fields=[],
        only_published=True, only_route_eligible=False, total_exported=1,
        by_city={"z": 1}, by_category={}, breakdown={},
    ))
    (root / "export.csv").write_text("id,slug\n1,test-place\n", encoding="utf-8")
    (root / "enriched.csv").write_text(
        "id,slug,title,suggested_address,suggested_short_description,suggested_price_level\n"
        "1,test-place,T,New Addr,New desc,2\n", encoding="utf-8",
    )
    place = _place()
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = place
    db.query.return_value.filter.return_value.all.return_value = [place]
    with patch("services.place_enrichment_import.apply_changes.write_admin_audit_log") as audit:
        result = run_import_apply(db, bid, actor="admin")
    assert result.rows_updated == 1
    assert place.address == "New Addr"
    assert place.short_description == "New desc"
    assert place.price_level == 2
    audit.assert_called_once()
    archived = batch_root / "archive" / bid
    assert (archived / "import.result.json").exists()
    assert not root.exists()


def test_export_csv_not_overwritten(batch_root):
    place = _place()
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = MagicMock(name="C")
    req = PlaceEnrichmentExportRequest(city_slug="zelenogradsk", limit=5, git_artifact=True)
    with (
        patch("services.place_enrichment_service.query_places_for_enrichment", return_value=[place]),
        patch("services.place_enrichment_service.write_admin_audit_log"),
        patch("services.place_enrichment_service.make_batch_id", return_value="place_enrichment_zelenogradsk_20260101_120000"),
    ):
        run_enrichment_export(db, req, actor="t")
    path = batch_root / "active" / "place_enrichment_zelenogradsk_20260101_120000" / "export.csv"
    original = path.read_text(encoding="utf-8")
    with (
        patch("services.place_enrichment_service.query_places_for_enrichment", return_value=[place]),
        patch("services.place_enrichment_service.write_admin_audit_log"),
        patch("services.place_enrichment_service.make_batch_id", return_value="place_enrichment_zelenogradsk_20260101_120001"),
    ):
        run_enrichment_export(db, req, actor="t")
    assert path.read_text(encoding="utf-8") == original
