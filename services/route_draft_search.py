from __future__ import annotations

from sqlalchemy.orm import Session

from models.place import Place
from models.route_draft import RouteDraft
from schemas.route_draft import PlaceSearchCandidateRead
from services.route_draft_loader import route_place_ids
from services.route_draft_quality import place_quality
from services.route_draft_rules import category_for_query, eligible_place_query, normalize_text

CATEGORY_SEARCH_GROUPS: dict[str, set[str]] = {
    "cafe": {"cafe", "coffee"},
    "food": {"cafe", "coffee", "food", "restaurant", "bar", "bakery"},
    "museum": {"museum"},
    "park": {"park"},
    "walk": {"walk", "park", "viewpoint", "landmark", "historic", "monument"},
}


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
    normalized = normalize_text(effective_query)
    category = category_for_query(effective_query)
    candidates = _candidate_pool(db, draft, category, normalized)
    ranked = sorted(candidates, key=lambda place: _rank(place, draft, normalized, category), reverse=True)
    return [_payload(place, draft, normalized, category) for place in ranked[:limit]]


def _effective_query(draft: RouteDraft, query: str | None, action: str, point_id: int | None) -> str:
    if query or action != "replace" or point_id is None:
        return query or ""
    point = next((item for item in draft.points if item.id == point_id), None)
    return point.place.category if point is not None and point.place.category else ""


def _candidate_pool(db: Session, draft: RouteDraft, category: str | None, normalized_query: str) -> list[Place]:
    excluded = route_place_ids(draft) | {int(item) for item in (draft.user_removed_place_ids or [])}
    query = eligible_place_query(db.query(Place), draft.city_id)
    if category:
        query = query.order_by((Place.category.in_(list(_category_group(category)))).desc())
    candidates = [place for place in query.limit(300).all() if place.id not in excluded]
    if not normalized_query and not category:
        return candidates
    return [place for place in candidates if _matches_search(place, normalized_query, category)]


def _rank(place: Place, draft: RouteDraft, normalized_query: str, category: str | None) -> float:
    category_match = category is not None and (place.category or "") in _category_group(category)
    text_match = bool(normalized_query and normalized_query in _search_text(place))
    match = 2.0 if category_match else 0.0
    match += 1.0 if text_match else 0.0
    return match + place_quality(place, float(draft.start_lat or 0), float(draft.start_lng or 0))


def _payload(place: Place, draft: RouteDraft, normalized_query: str, category: str | None) -> PlaceSearchCandidateRead:
    score = _rank(place, draft, normalized_query, category)
    category_match = category is not None and (place.category or "") in _category_group(category)
    reason = "category_match" if category_match else "name_match"
    return PlaceSearchCandidateRead(
        place_id=place.id,
        title=place.title,
        category=place.category,
        address=place.address,
        fit_reason=reason,
        estimated_extra_minutes=0,
        score=round(score, 4),
    )


def _matches_search(place: Place, normalized_query: str, category: str | None) -> bool:
    if category and (place.category or "") in _category_group(category):
        return True
    return bool(normalized_query and normalized_query in _search_text(place))


def _search_text(place: Place) -> str:
    return normalize_text(" ".join(filter(None, [place.title, place.address, place.category])))


def _category_group(category: str) -> set[str]:
    return CATEGORY_SEARCH_GROUPS.get(category, {category})
