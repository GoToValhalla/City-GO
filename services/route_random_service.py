from __future__ import annotations

import random
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from models.route_draft import RouteDraft
from schemas.route_draft import RandomRouteRequest
from schemas.start_point import ResolveStartRequest
from services.route_draft_recalc import recalculate_draft
from services.route_draft_rules import eligible_place_query, warning
from services.route_random_select import point_for_place, select_random_places
from services.start_point_service import resolve_start


def create_random_route_draft(db: Session, payload: RandomRouteRequest) -> RouteDraft | None:
    city = db.query(City).filter(City.slug == payload.city_slug).first()
    if city is None:
        return None
    start = _start_payload(db, city, payload)
    seed = payload.seed if payload.seed is not None else random.randint(1, 2_147_483_647)
    categories = _selected_categories(payload)
    draft = _draft(city, payload, start, seed, categories)
    db.add(draft)
    db.flush()
    candidates = eligible_place_query(db.query(Place), city.id).all()
    selected, used_fallback = select_random_places(candidates, draft, categories)
    draft.points = [point_for_place(place, index) for index, place in enumerate(selected, start=1)]
    draft.warnings = _warnings(candidates, selected, used_fallback, start)
    recalculate_draft(draft)
    db.commit()
    db.refresh(draft)
    return draft


def _start_payload(db: Session, city: City, payload: RandomRouteRequest) -> dict[str, object]:
    if payload.start is None:
        return {"type": "city_center", "lat": city.center_lat, "lng": city.center_lng, "label": "Центр города", "warnings": []}
    resolved = resolve_start(db, _resolve_request(city.slug, payload)) if payload.start.type != "city_center" else None
    if resolved:
        return resolved
    return {"type": "city_center", "lat": city.center_lat, "lng": city.center_lng, "label": "Центр города", "warnings": []}


def _resolve_request(city_slug: str, payload: RandomRouteRequest) -> ResolveStartRequest:
    start = payload.start
    return ResolveStartRequest(
        city_slug=city_slug,
        type=start.type if start else "city_center",
        lat=start.lat if start else None,
        lng=start.lng if start else None,
        query=(start.query or start.label) if start else None,
        place_id=start.place_id if start else None,
    )


def _selected_categories(payload: RandomRouteRequest) -> list[str]:
    if payload.category_mode != "balanced":
        return []
    return sorted({item.strip() for item in payload.selected_category_slugs if item.strip()})


def _draft(city: City, payload: RandomRouteRequest, start: dict[str, object], seed: int, categories: list[str]) -> RouteDraft:
    mode = "balanced" if categories else "none"
    return RouteDraft(
        city_id=city.id,
        session_token=payload.session_token,
        start_lat=float(start.get("lat") or city.center_lat or 0.0),
        start_lng=float(start.get("lng") or city.center_lng or 0.0),
        start_label=str(start.get("label") or "Центр города"),
        start_type=str(start.get("type") or "city_center"),
        budget_minutes=payload.budget_minutes,
        random_seed=seed,
        selected_category_slugs=categories,
        category_mode=mode,
        expires_at=datetime.utcnow() + timedelta(hours=24),
    )


def _warnings(candidates: list[Place], selected: list[Place], used_fallback: bool, start: dict[str, object]) -> list[dict[str, str]]:
    if not candidates:
        return [warning("NO_ELIGIBLE_PLACES", "В городе пока нет подходящих мест для маршрута.")]
    extra = list(start.get("warnings") or [])
    if used_fallback or len(selected) < 2:
        extra.append(warning("RANDOM_FALLBACK_USED", "Маршрут собран частично из лучших доступных мест."))
    return extra
