from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


FORBIDDEN_ACTIVE_REFERENCES = {
    "legacy place change review model": {
        "needle": "Place" + "Change" + "Review",
        "allowed_paths": {
            "models/place_change_review.py",
            "docs/architecture/legacy_code_register.md",
            "tests/test_legacy_source_of_truth_contracts.py",
        },
        "active_roots": ("routers", "services", "tests", "scripts", "telegram_bot"),
    },
    "legacy place change review table": {
        "needle": "place" + "_change" + "_reviews",
        "allowed_paths": {
            "models/place_change_review.py",
            "docs/architecture/legacy_code_register.md",
            "tests/test_legacy_source_of_truth_contracts.py",
        },
        "active_roots": ("routers", "services", "tests", "scripts", "telegram_bot"),
    },
}


def _iter_source_files() -> list[Path]:
    roots = ("routers", "services", "tests", "scripts", "telegram_bot", "models", "docs")
    files: list[Path] = []
    for root in roots:
        root_path = REPO_ROOT / root
        if not root_path.exists():
            continue
        files.extend(path for path in root_path.rglob("*") if path.suffix in {".py", ".md"})
    return files


def test_active_code_does_not_use_legacy_place_change_review_source_of_truth() -> None:
    violations: list[str] = []
    for label, rule in FORBIDDEN_ACTIVE_REFERENCES.items():
        needle = str(rule["needle"])
        allowed_paths = set(rule["allowed_paths"])
        active_roots = tuple(rule["active_roots"])
        for path in _iter_source_files():
            rel = path.relative_to(REPO_ROOT).as_posix()
            if rel in allowed_paths:
                continue
            if not rel.startswith(active_roots):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if needle in text:
                violations.append(f"{label}: {rel}")
    assert violations == []


def test_admin_place_change_review_contract_points_to_review_queue_item() -> None:
    router = (REPO_ROOT / "routers/admin_place_change_review.py").read_text(encoding="utf-8")
    service = (REPO_ROOT / "services/place_change_review_service.py").read_text(encoding="utf-8")

    assert "approve_place_change" in router
    assert "reject_place_change" in router
    assert "ReviewQueueItem" in service
    assert "field_name == \"place_change\"" in service or 'field_name == "place_change"' in service
    assert "status == \"open\"" in service or 'status == "open"' in service
