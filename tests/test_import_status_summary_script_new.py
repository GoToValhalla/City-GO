import json
import subprocess
import sys
from pathlib import Path


SCRIPT = Path("scripts/build_import_status_summary.py")


def _summary(payload: dict) -> dict[str, str]:
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=True,
    )
    return dict(line.split("=", 1) for line in result.stdout.splitlines())


def test_import_status_summary_uses_import_diff_new() -> None:
    payload = {
        "status": "success",
        "is_city_active": True,
        "can_publish": True,
        "step_details": {
            "import_diff": {"created": 3, "updated": 2, "rejected": 1},
            "warnings": [{"step": "finding_images", "error": "photo api down"}],
        },
    }

    summary = _summary(payload)

    assert summary["job_status"] == "success"
    assert summary["city_active"] == "true"
    assert summary["can_publish"] == "true"
    assert summary["created"] == "3"
    assert summary["updated"] == "2"
    assert summary["rejected"] == "1"
    assert summary["warnings_count"] == "1"
    assert summary["warning_1_step"] == "finding_images"
    assert summary["warning_1_error"] == "photo api down"


def test_import_status_summary_falls_back_to_import_summary_new() -> None:
    summary = _summary({"step_details": {"import_summary": {"hidden": 4, "needs_review": 5}}})

    assert summary["hidden"] == "4"
    assert summary["needs_review"] == "5"


def test_import_status_summary_handles_missing_step_details_new() -> None:
    summary = _summary({"status": "queued", "places_total": 0})

    assert summary["job_status"] == "queued"
    assert summary["places_total"] == "0"
    assert summary["created"] == "0"
    assert summary["warnings_count"] == "0"
    assert summary["warning_1_step"] == ""
    assert summary["warning_1_error"] == ""


def test_import_status_summary_counts_changed_ids_without_printing_them_new() -> None:
    ids = list(range(1, 101))
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps({"step_details": {"import_diff": {"changed_place_ids": ids}}}),
        text=True,
        capture_output=True,
        check=True,
    )

    assert "changed_place_ids_count=100" in result.stdout
    assert "changed_place_ids=" not in result.stdout
    assert "1, 2, 3" not in result.stdout


def test_import_status_summary_kutaisi_partial_success_payload_new() -> None:
    payload = {
        "status": "partial_success",
        "current_step": "ready_for_review",
        "launch_status": "published",
        "places_total": 1534,
        "scopes_succeeded": 3,
        "step_details": {"import_diff": {"created": 931, "rejected": 468}},
    }

    summary = _summary(payload)

    assert summary["job_status"] == "partial_success"
    assert summary["current_step"] == "ready_for_review"
    assert summary["launch_status"] == "published"
    assert summary["places_total"] == "1534"
    assert summary["created"] == "931"
    assert summary["rejected"] == "468"
    assert summary["scopes_succeeded"] == "3"
