from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from db.session import SessionLocal
from models.category import Category
from models.city import City
from models.city_candidate import CityCandidate
from models.city_import_job import CityImportJob
from models.city_import_scope import CityImportScope
from models.collection import Collection
from models.collection_place import CollectionPlace
from models.country import Country
from models.place import Place
from models.place_schedule import PlaceSchedule
from models.place_tag import PlaceTag
from models.region import Region
from models.route import Route
from models.route_place import RoutePlace
from models.tag import Tag
from services.import_job_service import lock_scope, unlock_scope


def lock_target(target: dict[str, Any], now: datetime, force: bool) -> dict[str, Any]:
    with SessionLocal() as db:
        city = db.query(City).filter(City.slug == target["city"]).first()
        if city is None:
            return {"status": "failed", "error": "city_not_found"}
        scope = _ensure_scope(db, city.id, target, now)
        if scope.status == "paused" or not scope.enabled:
            return {"status": "skipped", "reason": "scope_disabled"}
        if not _due(scope, now, force):
            return {"status": "skipped", "reason": "not_due"}
        status = "locked" if lock_scope(db, scope, now) else "locked_elsewhere"
        return {"status": status}


def schedule_next(target: dict[str, Any]) -> None:
    with SessionLocal() as db:
        scope = _scope_by_target(db, target)
        if scope is None:
            return
        scope.last_imported_at = datetime.utcnow()
        scope.next_run_at = scope.last_imported_at + timedelta(hours=scope.refresh_interval_hours or 168)
        db.commit()


def unlock_target(target: dict[str, Any]) -> None:
    with SessionLocal() as db:
        scope = _scope_by_target(db, target)
        if scope is not None:
            unlock_scope(db, scope)


def _ensure_scope(db: Any, city_id: int, target: dict[str, Any], now: datetime) -> CityImportScope:
    scope = db.query(CityImportScope).filter_by(city_id=city_id, code=target["scope"]).first()
    if scope is None:
        scope = CityImportScope(city_id=city_id, code=target["scope"], name=target["scope"])
        db.add(scope)
    scope.bbox = target["bbox"]
    scope.import_profile = target["profile"]
    scope.enabled = True
    scope.status = "enabled" if scope.status == "draft" else scope.status
    scope.refresh_interval_hours = target["refresh_interval_hours"]
    scope.next_run_at = scope.next_run_at or now
    db.commit()
    db.refresh(scope)
    return scope


def _scope_by_target(db: Any, target: dict[str, Any]) -> CityImportScope | None:
    city = db.query(City).filter(City.slug == target["city"]).first()
    if city is None:
        return None
    return db.query(CityImportScope).filter_by(city_id=city.id, code=target["scope"]).first()


def _due(scope: CityImportScope, now: datetime, force: bool) -> bool:
    return force or scope.next_run_at is None or scope.next_run_at <= now
