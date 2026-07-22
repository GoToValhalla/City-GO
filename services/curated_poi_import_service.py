from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from models.category import Category
from models.city import City
from models.city_import_scope import CityImportScope
from models.place import Place
from models.place_scope_link import PlaceScopeLink
from services.coverage_scope_policy import resolve_scope_policy
from services.place_change_review_service import propose_place_change
from services.publication_state_writer import InvalidPublicationTransition, reconcile_published_place_state

ROOT_DIR = Path(__file__).resolve().parents[1]
CURATED_POI_DIR = ROOT_DIR / "data" / "config" / "curated_poi"


@dataclass(frozen=True)
class CuratedPoiImportResult:
    city: str
    scope: str
    loaded: int
    created: int
    updated: int
    skipped: int


def import_curated_poi_scope(db: Session, *, city_slug: str, scope_code: str, apply: bool = False) -> CuratedPoiImportResult:
    city = db.query(City).filter(City.slug == city_slug).first()
    if city is None:
        raise ValueError(f"Unknown city: {city_slug}")
    scope = db.query(CityImportScope).filter_by(city_id=city.id, code=scope_code).first()
    if scope is None:
        raise ValueError(f"Unknown scope: {city_slug}/{scope_code}")
    rows = _load_rows(city_slug, scope_code)
    if not apply:
        return CuratedPoiImportResult(city_slug, scope_code, len(rows), 0, 0, 0)

    policy = resolve_scope_policy(scope)
    created = updated = skipped = 0
    for row in rows:
        if not _valid(row):
            skipped += 1
            continue
        category_code = str(row.get("category") or "culture")
        category = _category(db, category_code)
        place = _find_existing(db, city.id, row)
        if place is None:
            place = Place(
                city_id=city.id,
                category_id=category.id,
                slug=str(row.get("slug") or _slug(city.slug, row)),
                title=str(row["title"]),
                short_description=row.get("short_description") or row.get("description"),
                category=category_code,
                canonical_category=str(row.get("canonical_category") or category_code),
                address=row.get("address"),
                lat=float(row["lat"]),
                lng=float(row["lng"]),
                source="curated_poi",
                source_url=row.get("source_url"),
                confidence=float(row.get("confidence") or 0.95),
                status="active",
                lifecycle_status="active",
                is_active=True,
                is_published=False,
                is_visible_in_catalog=False,
                is_route_eligible=False,
                is_searchable=False,
                publication_status="needs_review",
                place_layer=str(row.get("place_layer") or "tourist_catalog"),
                route_policy=str(row.get("route_policy") or policy.route_policy),
                tourist_eligible=bool(row.get("tourist_eligible", True)),
                transport_required=bool(row.get("transport_required", policy.transport_required)),
                route_exclusion_reason="transport_required_scope" if policy.transport_required else None,
                # No fallback to a fabricated default: if the curated row
                # doesn't specify a real visit duration, the field stays
                # NULL rather than inventing one that would be treated as
                # genuine evidence by quality scoring/coverage checks.
                average_visit_duration_minutes=_curated_visit_duration(row),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(place)
            db.flush()
            created += 1
        else:
            proposed = {
                "title": str(row["title"]),
                "category_id": category.id,
                "category": category_code,
                "canonical_category": str(row.get("canonical_category") or category_code),
                "lat": float(row["lat"]),
                "lng": float(row["lng"]),
                "source_url": row.get("source_url") or place.source_url,
                "place_layer": str(row.get("place_layer") or place.place_layer or "tourist_catalog"),
                "route_policy": str(row.get("route_policy") or policy.route_policy),
                "transport_required": bool(row.get("transport_required", policy.transport_required)),
            }
            if propose_place_change(db, place=place, proposed=proposed, reason="curated_poi_reimport"):
                place.title = proposed["title"]
                place.category_id = proposed["category_id"]
                place.category = proposed["category"]
                place.canonical_category = proposed["canonical_category"]
                place.lat = proposed["lat"]
                place.lng = proposed["lng"]
                place.source_url = proposed["source_url"]
                place.place_layer = proposed["place_layer"]
                place.route_policy = proposed["route_policy"]
                place.transport_required = proposed["transport_required"]
                computed_eligible = bool(place.is_route_eligible and not place.transport_required)
                if place.is_published:
                    db.flush()
                    try:
                        reconcile_published_place_state(
                            db, place,
                            route_eligible=computed_eligible,
                            route_exclusion_reason=None if computed_eligible else "transport_required_scope",
                            actor="curated_poi_import",
                            source="curated_poi_import_service",
                        )
                    except InvalidPublicationTransition:
                        pass
                place.updated_at = datetime.utcnow()
                updated += 1
        _link(db, place.id, scope.id)
    db.flush()
    return CuratedPoiImportResult(city_slug, scope_code, len(rows), created, updated, skipped)


def _load_rows(city_slug: str, scope_code: str) -> list[dict[str, Any]]:
    path = CURATED_POI_DIR / city_slug / f"{scope_code}.json"
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, list) else []


def _valid(row: dict[str, Any]) -> bool:
    return bool(row.get("title") and row.get("lat") is not None and row.get("lng") is not None)


def _curated_visit_duration(row: dict[str, Any]) -> int | None:
    value = row.get("average_visit_duration_minutes")
    return int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _find_existing(db: Session, city_id: int, row: dict[str, Any]) -> Place | None:
    source_url = row.get("source_url")
    if source_url:
        existing = db.query(Place).filter_by(city_id=city_id, source_url=source_url).first()
        if existing:
            return existing
    slug = row.get("slug")
    if slug:
        return db.query(Place).filter_by(city_id=city_id, slug=slug).first()
    return None


def _category(db: Session, code: str) -> Category:
    category = db.query(Category).filter(Category.code == code).first()
    if category:
        return category
    category = Category(code=code, name=code, is_active=True, created_at=datetime.utcnow(), updated_at=datetime.utcnow())
    db.add(category)
    db.flush()
    return category


def _link(db: Session, place_id: int, scope_id: int) -> None:
    existing = db.query(PlaceScopeLink).filter_by(place_id=place_id, scope_id=scope_id).first()
    if existing:
        existing.updated_at = datetime.utcnow()
        return
    db.add(PlaceScopeLink(place_id=place_id, scope_id=scope_id, relation_type="curated_poi"))


def _slug(city_slug: str, row: dict[str, Any]) -> str:
    raw = str(row.get("title") or "curated-poi").lower()
    cleaned = "".join(ch if ch.isalnum() else "-" for ch in raw).strip("-")
    return f"{city_slug}-curated-{cleaned}"[:250]
