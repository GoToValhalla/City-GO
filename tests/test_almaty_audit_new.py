import pytest
from pathlib import Path

from data.scripts.almaty_audit.manifest import write_manifest
from data.scripts.almaty_audit.summary import write_summary


@pytest.mark.unit
def test_write_summary_from_empty_new(tmp_path: Path) -> None:
    write_summary(tmp_path, "алматы", ["batch1"])
    text = (tmp_path / "pipeline_summary_almaty.md").read_text(encoding="utf-8")
    assert "алматы" in text
    assert "batch1" in text


@pytest.mark.unit
def test_write_manifest_lists_files_new(tmp_path: Path) -> None:
    (tmp_path / "places_almaty_full.csv").write_text("id\n1\n", encoding="utf-8")
    write_manifest(tmp_path, {"places_almaty_full.csv": "test"})
    import json
    data = json.loads((tmp_path / "audit_manifest.json").read_text(encoding="utf-8"))
    assert len(data["files"]) == 1
