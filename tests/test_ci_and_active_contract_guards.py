from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_admin_import_contract_uses_admin_job_table() -> None:
    text = "\n".join(
        [
            _read("routers/admin_import_jobs.py"),
            _read("services/admin_city_import_job_service.py"),
            _read("services/admin_import_jobs_fast.py"),
        ]
    )
    assert "CityAdminImportJob" in text
    assert "models.city_admin_import_job" in text
    assert "models.city_import_job" not in text
    assert "CityImportJob" not in text


def test_active_user_routes_do_not_import_legacy_itinerary_stack() -> None:
    text = _read("routers/user_routes.py")
    assert "services.itinerary_" not in text
    assert "itinerary_service" not in text
    assert "UserRouteBuildService" in text


def test_telegram_dispatcher_uses_only_active_routers() -> None:
    text = _read("telegram_bot/main.py")
    assert "telegram_bot.handlers.route" not in text
    assert "admin_moderation_router" in text
    assert "catalog_router" in text
    assert "include_router(admin_moderation_router)" in text
    assert "include_router(catalog_router)" in text


def test_frontend_lint_script_can_fail_ci() -> None:
    text = _read("frontend/package.json")
    assert '"lint": "npx eslint ."' in text or '"lint": "eslint ."' in text
    suppressed = "eslint . " + "||" + " true"
    assert suppressed not in text


def test_full_autotests_are_not_manual_only() -> None:
    text = _read(".github/workflows/ci.yml")
    assert "push:" in text
    assert "pull_request:" in text
    assert "workflow_dispatch:" in text
    assert "branches:" in text
    assert "- main" in text
