from __future__ import annotations

from collections import Counter

from models.route_draft import RouteDraft, RouteDraftPoint
from schemas.route_draft import CategorySummaryRead, DraftPointRead, RouteDraftRead, RouteWarningRead


def serialize_draft(draft: RouteDraft) -> RouteDraftRead:
    points = sorted(draft.points, key=lambda item: item.position)
    return RouteDraftRead(
        draft_id=draft.id,
        version=draft.version,
        route_status=draft.route_status,
        total_minutes=draft.total_minutes,
        budget_minutes=draft.budget_minutes,
        category_mode=draft.category_mode,
        selected_category_slugs=list(draft.selected_category_slugs or []),
        points=[_point(item) for item in points],
        warnings=[RouteWarningRead(**item) for item in (draft.warnings or [])],
        category_summary=_summary(draft, points),
    )


def _point(item: RouteDraftPoint) -> DraftPointRead:
    place = item.place
    return DraftPointRead(
        id=item.id,
        place_id=place.id,
        position=item.position,
        title=place.title,
        slug=place.slug,
        category=place.category,
        lat=float(place.lat),
        lng=float(place.lng),
        visit_minutes=item.visit_minutes,
        open_status=item.open_status,
        user_locked=item.user_locked,
        inserted_by_user=item.inserted_by_user,
        replacement_of_place_id=item.replacement_of_place_id,
        walk_minutes_from_prev=item.walk_minutes_from_prev,
        walk_minutes_to_next=item.walk_minutes_to_next,
    )


def _summary(draft: RouteDraft, points: list[RouteDraftPoint]) -> CategorySummaryRead:
    requested = list(draft.selected_category_slugs or [])
    counts = Counter(item.place.category for item in points if item.place.category)
    matched = {category: int(counts.get(category, 0)) for category in requested}
    neutral = sum(1 for item in points if item.place.category not in requested)
    missing = [category for category in requested if matched.get(category, 0) == 0]
    return CategorySummaryRead(requested=requested, matched=matched, neutral_added=neutral, missing=missing)
