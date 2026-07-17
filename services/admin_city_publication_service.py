from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from services.admin_audit_service import write_admin_audit_log
from services.canonical_publication_apply import apply_admin_city_publication_place
from services.place_publication_eligibility import city_publication_gate, place_publication_eligibility

CITY_STATUS_DRAFT = "draft"
CITY_STATUS_PUBLISHED = "published"
CITY_STATUS_REVIEW_REQUIRED = "review_required"
CITY_STATUS_UNPUBLISHED = "unpublished"

PLACE_PUBLICATION_PUBLISHED = "published"
PLACE_PUBLICATION_NEEDS_REVIEW = "needs_review"
PLACE_PUBLICATION_UNPUBLISHED = "unpublished"


@dataclass(frozen=True)
class CityPublicationResult:
    city: City
    places_total: int
    places_published: int
    places_hidden: int


@dataclass(frozen=True)
class CityPublicationPreview:
    city_id: int
    gate_allowed: bool
    gate_reasons: tuple[str, ...]
    places_total: int
    would_publish_place_ids: tuple[int, ...]
    would_hide_place_ids: tuple[int, ...]
    hide_reasons_by_place_id: dict[int, tuple[str, ...]]


def preview_city_publication(db: Session, city_id: int) -> CityPublicationPreview | None:
    """Read-only dry-run using the exact same gate and eligibility function
    publish_city itself uses, so dry-run and apply can never diverge."""
    city = db.query(City).filter(City.id == city_id).first()
    if city is None:
        return None

    gate = city_publication_gate(city)
    places = db.query(Place).filter(Place.city_id == city.id).order_by(Place.id.asc()).all()
    would_publish: list[int] = []
    would_hide: list[int] = []
    hide_reasons: dict[int, tuple[str, ...]] = {}
    for place in places:
        eligibility = place_publication_eligibility(place)
        if eligibility.eligible:
            would_publish.append(place.id)
        else:
            would_hide.append(place.id)
            hide_reasons[place.id] = eligibility.reasons

    return CityPublicationPreview(
        city_id=city.id,
        gate_allowed=gate.allowed,
        gate_reasons=gate.reasons,
        places_total=len(places),
        would_publish_place_ids=tuple(would_publish),
        would_hide_place_ids=tuple(would_hide),
        hide_reasons_by_place_id=hide_reasons,
    )


def publish_city(
    db: Session,
    city_id: int,
    *,
    actor: str,
    reason: str | None = None,
    override_readiness_gate: bool = False,
) -> CityPublicationResult | None:
    city = db.query(City).filter(City.id == city_id).with_for_update().first()
    if city is None:
        return None

    if not override_readiness_gate:
        gate = city_publication_gate(city)
        if not gate.allowed:
            raise ValueError(
                "Нельзя опубликовать город: не пройден readiness gate ("
                + ", ".join(gate.reasons)
                + "). Явный override_readiness_gate=true требуется для публикации без готового снапшота."
            )

    places = (
        db.query(Place)
        .filter(Place.city_id == city.id)
        .order_by(Place.id.asc())
        .with_for_update()
        .all()
    )
    publishable_places = [place for place in places if place_publication_eligibility(place).eligible]
    if not publishable_places:
        raise ValueError("Нельзя опубликовать город: нет ни одного места, прошедшего публичный quality gate.")

    now = datetime.utcnow()
    old_value = _city_publication_snapshot(city)
    published_ids = {place.id for place in publishable_places}
    published_count = 0
    hidden_count = 0

    for place in places:
        if place.id in published_ids:
            _publish_place_for_city(place, now=now, reason=reason)
            published_count += 1
        else:
            _hide_place_for_city_publication(place, now=now, reason="city_publication_quality_gate")
            hidden_count += 1

    city.launch_status = CITY_STATUS_PUBLISHED
    city.is_active = True
    city.last_import_at = city.last_import_at or now
    city.updated_at = now

    write_admin_audit_log(
        db,
        actor=actor,
        action="publish_city",
        entity_type="city",
        entity_id=city.id,
        old_value=old_value,
        new_value={
            **_city_publication_snapshot(city),
            "places_total": len(places),
            "places_published": published_count,
            "places_hidden": hidden_count,
            "readiness_gate_overridden": override_readiness_gate,
        },
        reason=reason,
    )
    db.commit()
    db.refresh(city)
    return CityPublicationResult(
        city=city,
        places_total=len(places),
        places_published=published_count,
        places_hidden=hidden_count,
    )


def unpublish_city(db: Session, city_id: int, *, actor: str, reason: str) -> CityPublicationResult | None:
    city = db.query(City).filter(City.id == city_id).with_for_update().first()
    if city is None:
        return None

    places = (
        db.query(Place)
        .filter(Place.city_id == city.id)
        .order_by(Place.id.asc())
        .with_for_update()
        .all()
    )
    now = datetime.utcnow()
    old_value = _city_publication_snapshot(city)

    for place in places:
        place.is_published = False
        place.is_visible_in_catalog = False
        place.is_searchable = False
        place.is_route_eligible = False
        place.publication_status = PLACE_PUBLICATION_UNPUBLISHED
        place.publication_comment = reason
        place.unpublished_at = now
        place.updated_at = now

    city.launch_status = CITY_STATUS_UNPUBLISHED
    city.is_active = False
    city.updated_at = now

    write_admin_audit_log(
        db,
        actor=actor,
        action="unpublish_city",
        entity_type="city",
        entity_id=city.id,
        old_value=old_value,
        new_value={
            **_city_publication_snapshot(city),
            "places_total": len(places),
            "places_published": 0,
            "places_hidden": len(places),
        },
        reason=reason,
    )
    db.commit()
    db.refresh(city)
    return CityPublicationResult(
        city=city,
        places_total=len(places),
        places_published=0,
        places_hidden=len(places),
    )


def _publish_place_for_city(place: Place, *, now: datetime, reason: str | None) -> None:
    apply_admin_city_publication_place(place, now=now, reason=reason)


def _hide_place_for_city_publication(place: Place, *, now: datetime, reason: str) -> None:
    place.is_published = False
    place.is_visible_in_catalog = False
    place.is_searchable = False
    place.is_route_eligible = False
    if not place.publication_status or place.publication_status == PLACE_PUBLICATION_PUBLISHED:
        place.publication_status = PLACE_PUBLICATION_NEEDS_REVIEW
    place.publication_comment = reason
    place.unpublished_at = now
    place.updated_at = now


def _city_publication_snapshot(city: City) -> dict[str, object]:
    return {
        "slug": city.slug,
        "launch_status": city.launch_status,
        "is_active": city.is_active,
        "readiness_score": city.readiness_score,
        "quality_status": city.quality_status,
    }
