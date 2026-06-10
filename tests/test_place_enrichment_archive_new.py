"""Tests for place enrichment batch archive and repair."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from services.place_enrichment_batch.archive import ArchiveIncompleteError, archive_batch, repair_batch_archive
from services.place_enrichment_batch.paths import REQUIRED_ARCHIVE_KEYS, batch_dir, batch_files_complete, batch_paths, make_batch_id
from services.place_enrichment_import_service import run_import_apply, run_import_preview, run_repair_archive


def _write_batch(root, bid: str) -> None:
    d = root / "active" / bid
    d.mkdir(parents=True)
    for name in ("export.csv", "enriched.csv", "import.preview.json", "import.result.json"):
        (d / name).write_text("x", encoding="utf-8")
    (d / "export.meta.json").write_text(
        '{"batch_id":"%s","status":"imported","city_slug":"z","limit":1,'
        '"missing_fields":[],"only_published":true,"only_route_eligible":false,'
        '"export_csv_path":"a","enriched_csv_path":"b","import_preview_path":"c",'
        '"import_result_path":"d","created_at":"2026-01-01T00:00:00",'
        '"total_exported":1,"by_city":{},"by_category":{},"missing_fields_breakdown":{}}' % bid,
        encoding="utf-8",
    )


@pytest.fixture()
def batch_root(tmp_path, monkeypatch):
    monkeypatch.setattr("services.place_enrichment_batch.paths.ROOT", tmp_path)
    monkeypatch.setattr("services.place_enrichment_batch.paths.ACTIVE", tmp_path / "active")
    monkeypatch.setattr("services.place_enrichment_batch.paths.ARCHIVE", tmp_path / "archive")
    return tmp_path


def test_apply_archives_full_batch_directory_new(batch_root):
    bid = make_batch_id("z")
    _write_batch(batch_root, bid)
    preview = {
        "batch_id": bid, "mode": "preview", "total_rows": 1, "rows_with_changes": 1,
        "changes": [{
            "place_id": 1, "slug": "test-place", "title": "T", "skipped": [],
            "updates": [{
                "field": "short_description", "old_value": "old", "new_value": "new",
                "source_column": "suggested_short_description",
            }],
        }],
        "skipped_rows": [], "unsupported_fields": {}, "errors": [],
    }
    import json
    root = batch_root / "active" / bid
    (root / "import.preview.json").write_text(json.dumps(preview), encoding="utf-8")
    place = MagicMock(id=1, slug="test-place", address="old", short_description="old")
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = place
    with patch("services.place_enrichment_import.apply_changes.write_admin_audit_log"):
        run_import_apply(db, bid, actor="admin")
    archived = batch_paths(bid, archived=True)
    assert batch_files_complete(archived)
    assert not batch_dir(bid, archived=False).exists()


def test_archive_contains_required_files_new(batch_root):
    bid = make_batch_id("z")
    _write_batch(batch_root, bid)
    archive_batch(bid)
    archived = batch_paths(bid, archived=True)
    for key in REQUIRED_ARCHIVE_KEYS:
        assert archived[key].exists(), key
    assert not batch_dir(bid, archived=False).exists()


def test_partial_archive_can_be_repaired_new(batch_root):
    bid = make_batch_id("khanty")
    _write_batch(batch_root, bid)
    partial = batch_root / "archive" / bid
    partial.mkdir(parents=True, exist_ok=True)
    (partial / "export.meta.json").write_text("{}", encoding="utf-8")
    path = repair_batch_archive(bid)
    archived = batch_paths(bid, archived=True)
    assert path.endswith(bid)
    assert batch_files_complete(archived)
    assert not batch_dir(bid, archived=False).exists()


def test_repair_service_without_db_new(batch_root):
    bid = make_batch_id("x")
    _write_batch(batch_root, bid)
    path = run_repair_archive(bid)
    assert (batch_root / "archive" / bid).as_posix() in path.replace("\\", "/")
    assert not batch_dir(bid, archived=False).exists()


def test_archive_incomplete_raises_new(batch_root):
    bid = make_batch_id("empty")
    (batch_root / "active" / bid).mkdir(parents=True)
    (batch_root / "active" / bid / "export.csv").write_text("x", encoding="utf-8")
    with pytest.raises(ArchiveIncompleteError):
        archive_batch(bid)


def _archived_enriched_batch(batch_root, bid: str) -> None:
    import json
    root = batch_root / "archive" / bid
    root.mkdir(parents=True)
    header = "id,slug,title,suggested_short_description,suggested_image_url"
    (root / "export.csv").write_text(f"{header}\n1,test-place,T,old,\n", encoding="utf-8")
    (root / "enriched.csv").write_text(
        f"{header}\n1,test-place,T,new desc,http://img.jpg\n", encoding="utf-8",
    )
    (root / "export.meta.json").write_text(
        json.dumps({
            "batch_id": bid, "status": "imported", "city_slug": "z", "limit": 1,
            "missing_fields": [], "only_published": True, "only_route_eligible": False,
            "export_csv_path": f"archive/{bid}/export.csv",
            "enriched_csv_path": f"archive/{bid}/enriched.csv",
            "import_preview_path": f"archive/{bid}/import.preview.json",
            "import_result_path": f"archive/{bid}/import.result.json",
            "created_at": "2026-01-01T00:00:00", "total_exported": 1,
            "by_city": {}, "by_category": {}, "missing_fields_breakdown": {},
            "next_action": "archived",
        }),
        encoding="utf-8",
    )
    (root / "import.preview.json").write_text("{}", encoding="utf-8")
    (root / "import.result.json").write_text("{}", encoding="utf-8")


def test_preview_reads_complete_archive_batch_new(batch_root):
    bid = make_batch_id("archived-only")
    _archived_enriched_batch(batch_root, bid)
    place = MagicMock(
        id=1, slug="test-place", title="T", address="addr", short_description="old",
    )
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = [place]
    preview = run_import_preview(db, bid)
    assert preview.rows_with_changes == 1
    assert (batch_root / "archive" / bid / "import.preview.json").exists()
    assert place.short_description == "old"


def test_apply_archived_batch_without_rearchive_new(batch_root):
    bid = make_batch_id("server-reapply")
    _archived_enriched_batch(batch_root, bid)
    preview = {
        "batch_id": bid, "mode": "preview", "total_rows": 1, "rows_with_changes": 1,
        "changes": [{
            "place_id": 1, "slug": "test-place", "title": "T", "skipped": [],
            "updates": [{
                "field": "short_description", "old_value": "old", "new_value": "new desc",
                "source_column": "suggested_short_description",
            }],
        }],
        "skipped_rows": [], "unsupported_fields": {"suggested_image_url": 1}, "errors": [],
    }
    import json
    arch = batch_root / "archive" / bid
    (arch / "import.preview.json").write_text(json.dumps(preview), encoding="utf-8")
    place = MagicMock(id=1, slug="test-place", address="addr", short_description="old")
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = place
    db.query.return_value.filter.return_value.all.return_value = [place]
    with patch("services.place_enrichment_import.apply_changes.write_admin_audit_log"):
        result = run_import_apply(db, bid, actor="admin", no_archive_if_archived=True)
    assert result.rows_updated == 1
    assert place.short_description == "new desc"
    assert batch_files_complete(batch_paths(bid, archived=True))
    assert not batch_dir(bid, archived=False).exists()
