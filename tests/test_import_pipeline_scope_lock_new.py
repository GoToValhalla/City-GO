from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from data.scripts import import_cron_db
from models.city import City
from models.city_admin_import_job import CityAdminImportJob
from models.city_import_scope import CityImportScope
from services.admin_city_import_runner import summarize_import_results
from services.import_pipeline.scope_errors import scope_failure_rows
from services.import_scope_lock import acquire_scope_lock, scope_lock_key


class _SessionContext:
    def __init__(self, session):
        self._session = session

    def __enter__(self):
        return self._session

    def __exit__(self, *args):
        return False


def _target(city_slug: str, scope_code: str, *, job_id: int | None = None) -> dict[str, object]:
    payload = {
        "city": city_slug,
        "scope": scope_code,
        "profile": scope_code,
        "bbox": {"south": 54.6, "west": 20.2, "north": 54.9, "east": 20.8},
        "refresh_interval_hours": 168,
    }
    if job_id is not None:
        payload["city_admin_import_job_id"] = job_id
    return payload


def test_same_job_can_lock_multiple_scopes_without_self_lock_new(db_session, monkeypatch) -> None:
    city = City(slug="lock-city", name="Lock City", country="Россия")
    db_session.add(city)
    db_session.flush()
    job = CityAdminImportJob(city_id=city.id, status="running", source="admin_city_import")
    scopes = [
        CityImportScope(city_id=city.id, code="tourist_core", name="Tourist", enabled=True, status="enabled"),
        CityImportScope(city_id=city.id, code="food_area", name="Food", enabled=True, status="enabled"),
    ]
    db_session.add_all([job, *scopes])
    db_session.commit()
    monkeypatch.setattr(import_cron_db, "SessionLocal", lambda: _SessionContext(db_session))
    now = datetime.utcnow()

    first = import_cron_db.lock_target(_target(city.slug, "tourist_core", job_id=job.id), now, True)
    assert first["status"] == "locked"
    import_cron_db.unlock_target(_target(city.slug, "tourist_core", job_id=job.id))

    second = import_cron_db.lock_target(_target(city.slug, "food_area", job_id=job.id), now, True)
    assert second["status"] == "locked"
    import_cron_db.unlock_target(_target(city.slug, "food_area", job_id=job.id))


def test_stale_scope_lock_is_reclaimed_for_retry_new(db_session) -> None:
    city = City(slug="stale-lock-city", name="Stale Lock City", country="Россия")
    db_session.add(city)
    db_session.flush()
    job = CityAdminImportJob(city_id=city.id, status="running", source="admin_city_import")
    scope = CityImportScope(
        city_id=city.id,
        code="tourist_core",
        name="Tourist",
        enabled=True,
        status="enabled",
        locked_at=datetime.utcnow() - timedelta(hours=2),
    )
    db_session.add_all([job, scope])
    db_session.commit()

    result = acquire_scope_lock(
        db_session,
        scope,
        datetime.utcnow(),
        force=True,
        city_admin_import_job_id=job.id,
    )

    db_session.refresh(scope)
    assert result["acquired"] is True
    assert scope.locked_at is not None


def test_different_active_job_still_gets_locked_elsewhere_new(db_session, monkeypatch) -> None:
    city = City(slug="blocked-lock-city", name="Blocked Lock City", country="Россия")
    db_session.add(city)
    db_session.flush()
    owner = CityAdminImportJob(city_id=city.id, status="running", source="admin_city_import", updated_at=datetime.utcnow())
    challenger = CityAdminImportJob(
        city_id=city.id,
        status="running",
        source="admin_city_import",
        updated_at=datetime.utcnow() - timedelta(minutes=5),
    )
    scope = CityImportScope(
        city_id=city.id,
        code="tourist_core",
        name="Tourist",
        enabled=True,
        status="enabled",
        locked_at=datetime.utcnow(),
    )
    db_session.add_all([owner, challenger, scope])
    db_session.commit()
    monkeypatch.setattr(import_cron_db, "SessionLocal", lambda: _SessionContext(db_session))

    blocked = import_cron_db.lock_target(_target(city.slug, "tourist_core", job_id=challenger.id), datetime.utcnow(), True)

    assert blocked["status"] == "locked_elsewhere"
    assert blocked["error"] == "locked_elsewhere"
    assert blocked["lock_key"] == scope_lock_key(scope)
    assert blocked["owner_job_id"] == owner.id
    assert blocked["current_job_id"] == challenger.id
    assert blocked["retryable"] is True


def test_scope_errors_preserve_locked_elsewhere_diagnostics_new() -> None:
    payload = {
        "results": [
            {
                "scope": "food_area",
                "profile": "food_and_coffee",
                "status": "locked_elsewhere",
                "error": "locked_elsewhere",
                "lock_key": "city:42:scope:food_area",
                "owner_job_id": 7,
                "current_job_id": 9,
                "stale": False,
                "retryable": True,
                "admin_hint": "Scope уже заблокирован другим import job.",
            }
        ]
    }
    summary = summarize_import_results(payload)
    row = summary["scope_errors"][0]

    assert row["kind"] == "scope_lock"
    assert row["lock_key"] == "city:42:scope:food_area"
    assert row["owner_job_id"] == 7
    assert row["current_job_id"] == 9
    assert row["stale"] is False
    assert row["admin_hint"] == "Scope уже заблокирован другим import job."
    assert scope_failure_rows(payload["results"]) == summary["scope_errors"]
