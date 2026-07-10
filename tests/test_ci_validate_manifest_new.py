"""Unit tests for scripts/ci_validate_manifest.py — the CI validation
manifest deploy.yml gates on. build_manifest computes validation_complete
truthfully; verify_manifest must fail closed on any missing/wrong/incomplete
manifest, never soft-pass."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.ci_validate_manifest import (
    REQUIRED_FIELDS,
    ManifestError,
    build_manifest,
    verify_manifest,
)


def _complete_manifest(**overrides) -> dict:
    base = build_manifest(
        target_sha="abc123",
        base_sha="def456",
        selection_mode="auto_ancestor",
        changed_files=["core/foo.py"],
        backend_required=True,
        frontend_required=False,
        workflow_validation_required=False,
        backend_result="success",
        frontend_result="skipped_not_required",
        workflow_validation_result="skipped_not_required",
    )
    base.update(overrides)
    return base


def test_build_manifest_has_all_required_fields_new() -> None:
    manifest = _complete_manifest()
    for field in REQUIRED_FIELDS:
        assert field in manifest


def test_build_manifest_complete_when_required_suites_succeed_new() -> None:
    manifest = _complete_manifest()
    assert manifest["validation_complete"] is True


def test_build_manifest_incomplete_when_required_suite_failed_new() -> None:
    manifest = build_manifest(
        target_sha="abc123",
        base_sha="def456",
        selection_mode="auto_ancestor",
        changed_files=[],
        backend_required=True,
        frontend_required=False,
        workflow_validation_required=False,
        backend_result="failed",
        frontend_result="skipped_not_required",
        workflow_validation_result="skipped_not_required",
    )
    assert manifest["validation_complete"] is False


def test_build_manifest_incomplete_when_required_suite_skipped_new() -> None:
    """A required suite reporting anything other than success — including an
    unexpected skip — must make validation_complete false."""
    manifest = build_manifest(
        target_sha="abc123",
        base_sha="def456",
        selection_mode="auto_ancestor",
        changed_files=[],
        backend_required=True,
        frontend_required=False,
        workflow_validation_required=False,
        backend_result="skipped_not_required",
        frontend_result="skipped_not_required",
        workflow_validation_result="skipped_not_required",
    )
    assert manifest["validation_complete"] is False


def test_build_manifest_complete_with_all_suites_required_and_passing_new() -> None:
    manifest = build_manifest(
        target_sha="abc123",
        base_sha="",
        selection_mode="full_explicit",
        changed_files=[],
        backend_required=True,
        frontend_required=True,
        workflow_validation_required=True,
        backend_result="success",
        frontend_result="success",
        workflow_validation_result="success",
    )
    assert manifest["validation_complete"] is True


def test_verify_manifest_passes_for_valid_complete_manifest_new() -> None:
    manifest = _complete_manifest()
    verify_manifest(manifest, expected_sha="abc123")  # must not raise


def test_verify_manifest_rejects_sha_mismatch_new() -> None:
    manifest = _complete_manifest()
    with pytest.raises(ManifestError, match="does not match"):
        verify_manifest(manifest, expected_sha="different-sha")


def test_verify_manifest_rejects_incomplete_validation_new() -> None:
    manifest = _complete_manifest(validation_complete=False)
    with pytest.raises(ManifestError, match="validation_complete=false"):
        verify_manifest(manifest, expected_sha="abc123")


def test_verify_manifest_rejects_missing_fields_new() -> None:
    manifest = _complete_manifest()
    del manifest["backend_result"]
    with pytest.raises(ManifestError, match="missing required fields"):
        verify_manifest(manifest, expected_sha="abc123")


def test_verify_manifest_rejects_required_suite_not_success_even_if_flag_says_complete_new() -> None:
    """Defense in depth: even if validation_complete was somehow set to True
    incorrectly, a required suite that isn't 'success' must still be rejected."""
    manifest = _complete_manifest(backend_result="failed", validation_complete=True)
    with pytest.raises(ManifestError, match="backend_result"):
        verify_manifest(manifest, expected_sha="abc123")


def test_cli_verify_fails_closed_on_missing_manifest_file_new() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/ci_validate_manifest.py", "verify", "--manifest-file", "/tmp/does-not-exist-manifest.json", "--expected-sha", "abc123"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "not found" in result.stderr


def test_cli_verify_fails_closed_on_invalid_json_new() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        bad_file = Path(tmp) / "manifest.json"
        bad_file.write_text("not valid json{", encoding="utf-8")
        result = subprocess.run(
            [sys.executable, "scripts/ci_validate_manifest.py", "verify", "--manifest-file", str(bad_file), "--expected-sha", "abc123"],
            capture_output=True,
            text=True,
        )
    assert result.returncode != 0
    assert "not valid JSON" in result.stderr


def test_cli_write_then_verify_round_trip_new() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        output_file = Path(tmp) / "manifest.json"
        write_result = subprocess.run(
            [
                sys.executable, "scripts/ci_validate_manifest.py", "write",
                "--target-sha", "abc123",
                "--base-sha", "def456",
                "--selection-mode", "auto_ancestor",
                "--backend-required",
                "--backend-result", "success",
                "--frontend-result", "skipped_not_required",
                "--workflow-validation-result", "skipped_not_required",
                "--output", str(output_file),
            ],
            capture_output=True,
            text=True,
        )
        assert write_result.returncode == 0, write_result.stderr
        assert output_file.exists()
        manifest = json.loads(output_file.read_text(encoding="utf-8"))
        assert manifest["validation_complete"] is True

        verify_result = subprocess.run(
            [sys.executable, "scripts/ci_validate_manifest.py", "verify", "--manifest-file", str(output_file), "--expected-sha", "abc123"],
            capture_output=True,
            text=True,
        )
    assert verify_result.returncode == 0, verify_result.stderr


def test_cli_write_exits_nonzero_when_incomplete_new() -> None:
    """The write command's own exit code must also reflect an incomplete
    validation, so a CI step that forgets to check the JSON still notices."""
    with tempfile.TemporaryDirectory() as tmp:
        output_file = Path(tmp) / "manifest.json"
        result = subprocess.run(
            [
                sys.executable, "scripts/ci_validate_manifest.py", "write",
                "--target-sha", "abc123",
                "--base-sha", "def456",
                "--selection-mode", "auto_ancestor",
                "--backend-required",
                "--backend-result", "failed",
                "--frontend-result", "skipped_not_required",
                "--workflow-validation-result", "skipped_not_required",
                "--output", str(output_file),
            ],
            capture_output=True,
            text=True,
        )
    assert result.returncode != 0
