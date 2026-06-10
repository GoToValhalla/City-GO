"""Создание места в draft из админки."""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from models.place import Place
from models.place_tag import PlaceTag
from services.admin_audit_service import write_admin_audit_log
from services.product_event_service import record_event


def slugify_title(title: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9а-яА-ЯёЁ]+", "-", title.strip().lower()).strip("-")
    return slug or "place"


def create_draft_place(db: Session, payload: dict[str, object], *, actor: str) -> Place:
    city_id = int(payload["city_id"])
    title = str(payload["title"]).strip()
    slug = _unique_slug(db, str(payload.get("slug") or slugify_title(title)))
    if payload.get("lat") is None and payload.get("lng") is None and not payload.get("address"):
        raise ValueError("Укажите адрес или координаты")
    lat = float(payload.get("lat") or 0.0)
    lng = float(payload.get("lng") or 0.0)
    place = Place(
        city_id=city_id, slug=slug, title=title,
        category=str(payload.get("category") or "attraction"),
        address=payload.get("address"), source=str(payload.get("source") or "admin_manual"),
        short_description=payload.get("short_description"), lat=lat, lng=lng,
        publication_status="draft", is_published=False, is_visible_in_catalog=False,
        is_route_eligible=bool(payload.get("route_enabled", False)),
        is_searchable=False, verification_status="unverified", admin_comment=payload.get("admin_comment"),
    )
    db.add(place)
    db.flush()
    _sync_tags(db, place.id, payload.get("tag_ids") or [])
    write_admin_audit_log(db, actor=actor, action="create_place_draft", entity_type="place", entity_id=place.id,
                          new_value={"title": title, "publication_status": "draft"}, reason="Ручное создание")
    record_event(db, event_type="place_created", place_id=place.id, payload={"source": "admin"}, commit=False)
    db.commit()
    db.refresh(place)
    return place


def _unique_slug(db: Session, base: str) -> str:
    slug, idx = base, 2
    while db.query(Place).filter(Place.slug == slug).first():
        slug = f"{base}-{idx}"
        idx += 1
    return slug


def _sync_tags(db: Session, place_id: int, tag_ids: list[object]) -> None:
    for raw in tag_ids:
        db.add(PlaceTag(place_id=place_id, tag_id=int(raw)))
