from __future__ import annotations

from sqlalchemy.orm import Session

from models.place import Place
from models.route_draft import RouteDraft
from schemas.route_draft import PlaceSearchCandidateRead
from services.route_draft_loader import route_place_ids
from services.route_draft_quality import place_quality
from services.route_draft_rules import category_for_query, eligible_place_query, normalize_text


def search_places(
    db: Session,
    draft: RouteDraft,
    *,
    query: str | None,
    action: str,
    point_id: int | None,
    limit: int,
) -> list[PlaceSearchCandidateRead]:
    effective_query = _effective_query(draft, query, action, point_id)
    category = category_for_query(effective_query)
    candidates = _candidate_pool(db, draft, category)
    ranked = sorted(candidates, key=lambda place: _rank(place, draft, effective_query, category), reverse=True)
    return [_payload(place, draft, effective_query, category) for place in ranked[:limit]]


def _effective_query(draft: RouteDraft, query: str | None, action: str, point_id: int | None) -> str:
    if query or action != "replace" or point_id is None:
        return query or ""
    point = next((item for item in draft.points if item.id == point_id), None)
    return point.place.category if point is not None and point.place.category else ""


def _candidate_pool(db: Session, draft: RouteDraft, category: str | None) -> list[Place]:
    excluded = route_place_ids(draft) | {int(item) for item in (draft.user_removed_place_ids or [])}
    query = eligible_place_query(db.query(Place), draft.city_id)
    if category:
        query = query.order_by((Place.category == category).desc())
    return [place for place in query.limit(200).all() if place.id not in excluded]


def _rank(place: Place, draft: RouteDraft, query: str, category: str | None) -> float:
    text = normalize_text(" ".join(filter(None, [place.title, place.address, place.category])))
    normalized = normalize_text(query)
    match = 2.0 if category and place.category == category else 0.0
    match += 1.0 if normalized and normalized in text else 0.0
    return match + place_quality(place, float(draft.start_lat or 0), float(draft.start_lng or 0))


def _payload(place: Place, draft: RouteDraft, query: str, category: str | None) -> PlaceSearchCandidateRead:
    score = _rank(place, draft, query, category)
    reason = "category_match" if category and place.category == category else "name_or_quality_match"
    return PlaceSearchCandidateRead(
        place_id=place.id,
        title=place.title,
        category=place.category,
        address=place.address,
        fit_reason=reason,
        estimated_extra_minutes=0,
        score=round(score, 4),
    )
