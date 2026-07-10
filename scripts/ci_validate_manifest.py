#!/usr/bin/env python3
"""Create and verify the CI validation manifest that deploy.yml gates on.

`write` is called from ci.yml at the end of a run to record exactly what was
validated for a given commit. `verify` is called from deploy.yml's
resolve-and-gate job to fail closed if the manifest for the exact deploy SHA
is missing, malformed, incomplete, or reports a required suite as skipped or
failed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = (
    "target_sha",
    "base_sha",
    "selection_mode",
    "changed_files",
    "backend_required",
    "frontend_required",
    "workflow_validation_required",
    "backend_result",
    "frontend_result",
    "workflow_validation_result",
    "validation_complete",
)

OK_RESULTS = {"success", "skipped_not_required"}


def build_manifest(
    *,
    target_sha: str,
    base_sha: str,
    selection_mode: str,
    changed_files: list[str],
    backend_required: bool,
    frontend_required: bool,
    workflow_validation_required: bool,
    backend_result: str,
    frontend_result: str,
    workflow_validation_result: str,
) -> dict[str, Any]:
    """Build the manifest dict. `*_result` must be one of:
    "success", "failed", "skipped_not_required". A required suite reporting
    anything other than "success" makes validation_complete False.
    """
    checks = [
        (backend_required, backend_result),
        (frontend_required, frontend_result),
        (workflow_validation_required, workflow_validation_result),
    ]
    validation_complete = all(
        (result == "success") if required else (result in OK_RESULTS)
        for required, result in checks
    )
    return {
        "target_sha": target_sha,
        "base_sha": base_sha,
        "selection_mode": selection_mode,
        "changed_files": list(changed_files),
        "backend_required": bool(backend_required),
        "frontend_required": bool(frontend_required),
        "workflow_validation_required": bool(workflow_validation_required),
        "backend_result": backend_result,
        "frontend_result": frontend_result,
        "workflow_validation_result": workflow_validation_result,
        "validation_complete": bool(validation_complete),
    }


class ManifestError(ValueError):
    """Raised when a manifest fails verification. Message is operator-facing."""


def verify_manifest(manifest: dict[str, Any], *, expected_sha: str) -> None:
    """Raise ManifestError with a precise, truthful reason if the manifest
    does not prove the exact deploy SHA was fully validated. Never returns a
    partial/soft pass — every failure mode raises."""
    missing = [field for field in REQUIRED_FIELDS if field not in manifest]
    if missing:
        raise ManifestError(f"manifest is missing required fields: {', '.join(missing)}")

    manifest_sha = str(manifest["target_sha"])
    if manifest_sha != expected_sha:
        raise ManifestError(
            f"manifest target_sha ({manifest_sha}) does not match the exact deploy SHA ({expected_sha})"
        )

    if manifest["validation_complete"] is not True:
        raise ManifestError("manifest reports validation_complete=false")

    checks = (
        ("backend_required", "backend_result"),
        ("frontend_required", "frontend_result"),
        ("workflow_validation_required", "workflow_validation_result"),
    )
    for required_field, result_field in checks:
        if manifest[required_field] and manifest[result_field] != "success":
            raise ManifestError(
                f"{result_field} is '{manifest[result_field]}' but {required_field} is true — "
                "a required suite was skipped or failed"
            )


def _write_command(args: argparse.Namespace) -> int:
    changed_files = []
    if args.changed_files_file:
        path = Path(args.changed_files_file)
        if path.exists():
            changed_files = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    manifest = build_manifest(
        target_sha=args.target_sha,
        base_sha=args.base_sha,
        selection_mode=args.selection_mode,
        changed_files=changed_files,
        backend_required=args.backend_required,
        frontend_required=args.frontend_required,
        workflow_validation_required=args.workflow_validation_required,
        backend_result=args.backend_result,
        frontend_result=args.frontend_result,
        workflow_validation_result=args.workflow_validation_result,
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0 if manifest["validation_complete"] else 1


def _verify_command(args: argparse.Namespace) -> int:
    path = Path(args.manifest_file)
    if not path.exists():
        print(f"ERROR: CI validation manifest not found at {path}", file=sys.stderr)
        return 1
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR: CI validation manifest is not valid JSON: {exc}", file=sys.stderr)
        return 1
    try:
        verify_manifest(manifest, expected_sha=args.expected_sha)
    except ManifestError as exc:
        print(f"ERROR: CI validation manifest rejected: {exc}", file=sys.stderr)
        return 1
    print(f"CI validation manifest verified for {args.expected_sha}")
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    write_parser = subparsers.add_parser("write", help="Build and write the manifest (called from ci.yml)")
    write_parser.add_argument("--target-sha", required=True)
    write_parser.add_argument("--base-sha", required=True)
    write_parser.add_argument("--selection-mode", required=True)
    write_parser.add_argument("--changed-files-file", default="")
    write_parser.add_argument("--backend-required", action="store_true")
    write_parser.add_argument("--frontend-required", action="store_true")
    write_parser.add_argument("--workflow-validation-required", action="store_true")
    write_parser.add_argument("--backend-result", required=True, choices=["success", "failed", "skipped_not_required"])
    write_parser.add_argument("--frontend-result", required=True, choices=["success", "failed", "skipped_not_required"])
    write_parser.add_argument("--workflow-validation-result", required=True, choices=["success", "failed", "skipped_not_required"])
    write_parser.add_argument("--output", required=True)
    write_parser.set_defaults(func=_write_command)

    verify_parser = subparsers.add_parser("verify", help="Verify a downloaded manifest (called from deploy.yml)")
    verify_parser.add_argument("--manifest-file", required=True)
    verify_parser.add_argument("--expected-sha", required=True)
    verify_parser.set_defaults(func=_verify_command)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
