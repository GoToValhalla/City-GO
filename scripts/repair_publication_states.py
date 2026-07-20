from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.session import SessionLocal
from models.city import City, allow_city_product_state_change
from models.place import Place
from services.publication_state_writer import REASON_PUBLISHED, transition_place_publication

SNAPSHOT_DIR = Path("artifacts")
HARD_BLOCKER_STATUSES = {"closed", "temporarily_closed", "inactive", "archived"}
HARD_BLOCKER_LIFECYCLE = {"closed", "removed", "inactive", "archived", "permanently_closed"}
NON_ROUTE_CATEGORIES = {"service", "transport", "utility", "pharmacy", "bank", "atm"}


def _count_published_places(db: Session, city_id: int) -> int:
    return int(
        db.query(func.count(Place.id))
        .filter(Place.city_id == city_id, Place.is_published.is_(True))
        .scalar()
        or 0
    )


def _category_route_eligible(place: Place) -> bool:
    category = str(place.canonical_category or place.category or "").strip().lower()
    return category not in NON_ROUTE_CATEGORIES and bool(place.tourist_eligible)


def _has_hard_blocker(place: Place) -> bool:
    return bool(
        place.status in HARD_BLOCKER_STATUSES
        or place.lifecycle_status in HARD_BLOCKER_LIFECYCLE
        or place.is_spam_poi
        or place.is_duplicate_suspected
        or place.lat is None
        or place.lng is None
    )


def build_plan(
    db: Session,
    *,
    city_slug: str | None,
    restore_cities: bool,
    repair_place_flags: bool,
    limit: int | None,
) -> dict[str, Any]:
    city_query = db.query(City).order_by(City.id.asc())
    if city_slug:
        city_query = city_query.filter(City.slug == city_slug)
    city_changes: list[dict[str, Any]] = []
    place_changes: list[dict[str, Any]] = []

    if restore_cities:
        for city in city_query.all():
            published_places = _count_published_places(db, int(city.id))
            if published_places and (not city.is_active or city.launch_status != "published"):
                city_changes.append(
                    {
                        "city_id": city.id,
                        "slug": city.slug,
                        "name": city.name,
                        "from": {
                            "is_active": bool(city.is_active),
                            "launch_status": city.launch_status,
                        },
                        "to": {"is_active": True, "launch_status": "published"},
                        "published_places": published_places,
                    }
                )

    if repair_place_flags:
        query = (
            db.query(Place)
            .join(City, City.id == Place.city_id)
            .filter(Place.publication_status == "published")
        )
        if city_slug:
            query = query.filter(City.slug == city_slug)
        query = query.order_by(Place.id.asc())
        if limit:
            query = query.limit(limit)
        for place in query.all():
            desired_route = _category_route_eligible(place) and not _has_hard_blocker(place)
            desired = {
                "is_active": True,
                "is_published": True,
                "is_visible_in_catalog": True,
                "is_searchable": True,
                "is_route_eligible": desired_route,
            }
            current = {key: bool(getattr(place, key)) for key in desired}
            if current != desired:
                place_changes.append(
                    {
                        "place_id": place.id,
                        "city_id": place.city_id,
                        "title": place.title,
                        "from": current,
                        "to": desired,
                    }
                )
    return {"city_changes": city_changes, "place_changes": place_changes}


def apply_plan(db: Session, plan: dict[str, Any]) -> None:
    """Apply a previously reviewed plan in one caller-owned transaction."""

    savepoint = db.begin_nested()
    try:
        for item in plan["city_changes"]:
            city = (
                db.query(City)
                .filter(City.id == int(item["city_id"]))
                .with_for_update()
                .one_or_none()
            )
            if city is None:
                continue
            allow_city_product_state_change(city)
            city.is_active = True
            city.launch_status = "published"
            city.updated_at = datetime.utcnow()

        place_ids = sorted({int(item["place_id"]) for item in plan["place_changes"]})
        locked_places = (
            db.query(Place)
            .filter(Place.id.in_(place_ids))
            .order_by(Place.id.asc())
            .with_for_update()
            .populate_existing()
            .all()
            if place_ids
            else []
        )
        expected_by_id = {int(item["place_id"]): item for item in plan["place_changes"]}
        for place in locked_places:
            item = expected_by_id[int(place.id)]
            transition_place_publication(
                db,
                place,
                to_status="published",
                reason_code=REASON_PUBLISHED,
                actor="repair_publication_states",
                source="repair_script",
                reason_details={
                    "repair_kind": "published_flag_consistency",
                    "planned_from": item["from"],
                    "planned_to": item["to"],
                },
                human_comment="Repair published-state flag consistency",
                route_eligible_when_published=bool(item["to"]["is_route_eligible"]),
                lock_place=False,
            )
        savepoint.commit()
    except Exception:
        savepoint.rollback()
        raise


def write_snapshot(plan: dict[str, Any]) -> str:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = SNAPSHOT_DIR / (
        "publication_repair_snapshot_"
        + datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        + ".json"
    )
    path.write_text(
        json.dumps(plan, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return str(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--city-slug")
    parser.add_argument("--restore-cities", action="store_true")
    parser.add_argument("--repair-place-flags", action="store_true")
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()

    with SessionLocal() as db:
        plan = build_plan(
            db,
            city_slug=args.city_slug,
            restore_cities=args.restore_cities,
            repair_place_flags=args.repair_place_flags,
            limit=args.limit,
        )
        snapshot = write_snapshot(plan)
        if args.apply:
            apply_plan(db, plan)
            db.commit()
        print(
            json.dumps(
                {
                    "mode": "apply" if args.apply else "dry_run",
                    "snapshot": snapshot,
                    "city_changes": len(plan["city_changes"]),
                    "place_changes": len(plan["place_changes"]),
                    "plan": plan,
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )


if __name__ == "__main__":
    main()
