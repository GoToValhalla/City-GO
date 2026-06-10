"""Запись диагностики после генерации маршрута."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from models.city import City
from services.route_generation_diagnostics.candidate_audit import audit_city_pool, audit_geo_pool
from services.route_generation_diagnostics.persist import persist_generation_run


def record_canonical_generation(
    db: Session,
    *,
    city: City | None,
    ctx: object,
    request_payload: dict[str, Any],
    final_route: object,
    user_id: int | None = None,
) -> int | None:
    try:
        return _record_canonical_generation(
            db,
            city=city,
            ctx=ctx,
            request_payload=request_payload,
            final_route=final_route,
            user_id=user_id,
        )
    except Exception:
        return None


def _record_canonical_generation(
    db: Session,
    *,
    city: City | None,
    ctx: object,
    request_payload: dict[str, Any],
    final_route: object,
    user_id: int | None = None,
) -> int | None:
    if city is None:
        return None
    lat, lng = getattr(ctx, "location", (None, None))
    radius = int(getattr(ctx, "radius_meters", 0) or 0)
    audited = (
        audit_geo_pool(db, city=city, lat=float(lat), lng=float(lng), radius_meters=radius)
        if lat is not None and lng is not None and radius > 0
        else audit_city_pool(db, city=city)
    )
    selected_ids, scores = _selected_from_final(final_route)
    status = "success" if selected_ids else "failed"
    run = persist_generation_run(
        db,
        city_id=city.id,
        user_id=user_id,
        request_json=request_payload,
        status=status,
        failure_reason=None if selected_ids else "no_selected_places",
        audited=audited,
        selected_place_ids=selected_ids,
        scores_by_place_id=scores,
    )
    return run.id


def record_itinerary_generation(
    db: Session,
    *,
    city: City | None,
    request_payload: dict[str, Any],
    ordered_places: list[object],
    ranked_places: list[dict[str, object]] | None = None,
) -> int | None:
    try:
        return _record_itinerary_generation(
            db,
            city=city,
            request_payload=request_payload,
            ordered_places=ordered_places,
            ranked_places=ranked_places,
        )
    except Exception:
        return None


def _record_itinerary_generation(
    db: Session,
    *,
    city: City | None,
    request_payload: dict[str, Any],
    ordered_places: list[object],
    ranked_places: list[dict[str, object]] | None = None,
) -> int | None:
    if city is None:
        return None
    audited = audit_city_pool(db, city=city)
    selected_ids = {int(getattr(p, "id")) for p in ordered_places}
    scores = _scores_from_ranked(ranked_places or [])
    run = persist_generation_run(
        db,
        city_id=city.id,
        user_id=None,
        request_json=request_payload,
        status="success" if selected_ids else "failed",
        failure_reason=None if selected_ids else "no_selected_places",
        audited=audited,
        selected_place_ids=selected_ids,
        scores_by_place_id=scores,
        selection_reasons_by_place_id=_reasons_from_ranked(ranked_places or []),
    )
    return run.id


def _selected_from_final(final_route: object) -> tuple[set[int], dict[int, float]]:
    ids: set[int] = set()
    scores: dict[int, float] = {}
    for point in getattr(final_route, "points", []) or []:
        raw_id = getattr(point, "place_id", None)
        if raw_id is None:
            continue
        place_id = int(str(raw_id))
        ids.add(place_id)
        score = getattr(point, "score", None)
        if isinstance(score, (int, float)):
            scores[place_id] = float(score)
    return ids, scores


def _scores_from_ranked(ranked: list[dict[str, object]]) -> dict[int, float]:
    out: dict[int, float] = {}
    for item in ranked:
        place = item.get("place")
        score = item.get("score")
        if place is not None and isinstance(score, (int, float)):
            out[int(place.id)] = float(score)
    return out


def _reasons_from_ranked(ranked: list[dict[str, object]]) -> dict[int, list[str]]:
    out: dict[int, list[str]] = {}
    for item in ranked:
        place = item.get("place")
        reasons = item.get("reasons")
        if place is not None and isinstance(reasons, list):
            out[int(place.id)] = [str(r) for r in reasons]
    return out
