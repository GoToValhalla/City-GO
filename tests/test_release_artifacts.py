from pathlib import Path


def test_release_artifacts_exist() -> None:
    expected = (
        "scripts/backup_db.sh",
        "scripts/restore_db.sh",
        "scripts/release_smoke.sh",
        "scripts/release_checks.sh",
        "scripts/backend_quality_gate.py",
        "scripts/backend_quality_baseline.txt",
        "scripts/check_place_coverage_gate.py",
        ".github/workflows/ci.yml",
        "requirements-dev.txt",
        "docs/backup_restore.md",
        "docs/architecture/backend_quality_gate.md",
        "docs/release_checklist.md",
        "docs/mvp_release_candidate.md",
    )
    assert all(Path(path).exists() for path in expected)


def test_backup_scripts_require_environment_database_url() -> None:
    backup = Path("scripts/backup_db.sh").read_text()
    restore = Path("scripts/restore_db.sh").read_text()
    assert "DATABASE_URL is required" in backup
    assert "DATABASE_URL is required" in restore
    assert ".env" not in backup
    assert ".env" not in restore


def test_release_checks_run_place_coverage_gate() -> None:
    release_checks = Path("scripts/release_checks.sh").read_text()

    assert "scripts/check_place_coverage_gate.py" in release_checks


def test_release_checks_run_backend_quality_gate() -> None:
    release_checks = Path("scripts/release_checks.sh").read_text()

    assert "scripts/backend_quality_gate.py" in release_checks


def test_dev_requirements_include_pytest_cov() -> None:
    requirements = Path("requirements-dev.txt").read_text()

    assert "pytest-cov==" in requirements
