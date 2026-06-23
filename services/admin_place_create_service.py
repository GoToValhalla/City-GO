"""Создание места в draft из админки."""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from models.place import Place
from models.place_tag import PlaceTag
from services.admin_audit_service import write_admin_audit_log
from services.product_event_service import record_event
from services.slug_transliterate import transliterate_cyrillic


def slugify_title(title: str) -> str:
    latin = transliterate_cyrillic(title.strip().lower())
    slug = re.sub(r"[^a-z0-9]+", "-", latin).strip("-")
    return slug or "place"


def create_draft_place(db: Session, payload: dict[str, object], *, actor: str) -> Place:
    city_id = int(payload["city_id"])
    title = str(payload["title"]).strip()
    lat = float(payload["lat"])
    lng = float(payload["lng"])
    if abs(lat) < 0.000001 and abs(lng) < 0.000001:
        raise ValueError("Нельзя создать место с координатами 0,0")

    slug = _unique_slug(db, city_id, str(payload.get("slug") or slugify_title(title)))
    category = str(payload.get("category") or "attraction")
    place = Place(
        city_id=city_id,
        slug=slug,
        title=title,
        category=category,
        canonical_category=category,
        address=payload.get("address"),
        source=str(payload.get("source") or "admin_manual"),
        source_url=payload.get("source_url"),
        short_description=payload.get("short_description"),
        image_url=payload.get("image_url"),
        website=payload.get("website"),
        phone=payload.get("phone"),
        atmosphere=payload.get("atmosphere"),
        inside=payload.get("inside"),
        best_for=payload.get("best_for"),
        opening_hours=payload.get("opening_hours"),
        average_visit_duration_minutes=payload.get("average_visit_duration_minutes"),
        price_level=payload.get("price_level"),
        indoor=bool(payload.get("indoor", False)),
        outdoor=bool(payload.get("outdoor", False)),
        dog_friendly=bool(payload.get("dog_friendly", False)),
        family_friendly=bool(payload.get("family_friendly", False)),
        lat=lat,
        lng=lng,
        publication_status="draft",
        is_published=False,
        is_visible_in_catalog=False,
        is_route_eligible=bool(payload.get("route_enabled", False)),
        is_searchable=False,
        verification_status="unverified",
        admin_comment=payload.get("admin_comment"),
    )
    db.add(place)
    db.flush()
    _sync_tags(db, place.id, payload.get("tag_ids") or [])
    write_admin_audit_log(
        db,
        actor=actor,
        action="create_place_draft",
        entity_type="place",
        entity_id=place.id,
        new_value={
            "title": title,
            "city_id": city_id,
            "category": category,
            "lat": lat,
            "lng": lng,
            "publication_status": "draft",
        },
        reason="Ручное создание",
    )
    record_event(db, event_type="place_created", place_id=place.id, payload={"source": "admin"}, commit=False)
    db.commit()
    db.refresh(place)
    return place


def _unique_slug(db: Session, city_id: int, base: str) -> str:
    slug, index = base, 2
    while db.query(Place).filter(Place.city_id == city_id, Place.slug == slug).first():
        slug = f"{base}-{index}"
        index += 1
    return slug


def _sync_tags(db: Session, place_id: int, tag_ids: list[object]) -> None:
    for raw in tag_ids:
        db.add(PlaceTag(place_id=place_id, tag_id=int(raw)))
