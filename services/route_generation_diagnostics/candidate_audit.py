"""Аудит candidate pool для диагностики генерации."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from services.candidate_retrieval_service import CandidateRetrievalService
from services.place_public_visibility import public_route_place_conditions
from services.route_eligibility import evaluate_place_route_eligibility


MAX_AUDIT_PLACES = 400


@dataclass(frozen=True)
class AuditedCandidate:
    place: Place
    is_eligible: bool
    rejection_reasons: tuple[str, ...]
    score: float | None = None


def audit_geo_pool(
    db: Session,
    *,
    city: City,
    lat: float,
    lng: float,
    radius_meters: int,
) -> list[AuditedCandidate]:
    distance = CandidateRetrievalService()._distance_meters_expr(lat=lat, lng=lng)
    query = (
        select(Place)
        .where(
            Place.city_id == city.id,
            distance <= radius_meters,
            *public_route_place_conditions(),
        )
        .limit(MAX_AUDIT_PLACES)
    )
    places = list(db.execute(query).scalars().all())
    return [_audit_place(place, city) for place in places]


def audit_city_pool(db: Session, *, city: City) -> list[AuditedCandidate]:
    query = select(Place).where(Place.city_id == city.id).limit(MAX_AUDIT_PLACES)
    places = list(db.execute(query).scalars().all())
    return [_audit_place(place, city) for place in places]


def _audit_place(place: Place, city: City) -> AuditedCandidate:
    result = evaluate_place_route_eligibility(place, city=city)
    return AuditedCandidate(
        place=place,
        is_eligible=result.eligible,
        rejection_reasons=result.reasons,
    )
