"""Public draft serialization: read-only projection (never mutates ORM state)."""

from __future__ import annotations

from collections import Counter

from sqlalchemy.orm import Session

from models.place import Place
from models.route_draft import RouteDraft, RouteDraftPoint
from schemas.route_draft import CategorySummaryRead, DraftPointRead, RouteDraftRead, RouteWarningRead
from services.route_draft_rules import eligible_place_query
from services.route_geometry import walk_minutes_between


def serialize_draft(draft: RouteDraft) -> RouteDraftRead:
    """Serialize persisted draft as-is (admin/internal or post-mutation)."""
    points = sorted(draft.points, key=lambda item: item.position)
    return _build_read(draft, points, extra_warnings=[])


def serialize_public_draft_view(db: Session, draft: RouteDraft) -> RouteDraftRead:
    """Read-only public view: omit ineligible points without persisting changes."""
    eligible = _eligible_ids(db, draft)
    kept = [item for item in sorted(draft.points, key=lambda row: row.position) if int(item.place_id) in eligible]
    omitted = len(draft.points) - len(kept)
    extra: list[dict[str, str]] = []
    if omitted:
        extra.append(
            {
                "code": "STALE_POINTS_OMITTED",
                "message": "Некоторые точки временно скрыты: они больше не доступны для публичного маршрута.",
            }
        )
    return _build_read(draft, kept, extra_warnings=extra, ephemeral=True)


def _eligible_ids(db: Session, draft: RouteDraft) -> set[int]:
    place_ids = {int(item.place_id) for item in draft.points}
    if not place_ids:
        return set()
    return {
        int(row.id)
        for row in eligible_place_query(db.query(Place), draft.city_id).filter(Place.id.in_(place_ids)).all()
    }


def _build_read(
    draft: RouteDraft,
    points: list[RouteDraftPoint],
    *,
    extra_warnings: list[dict[str, str]],
    ephemeral: bool = False,
) -> RouteDraftRead:
    point_reads = [
        _point_read(item, index, points=points, draft=draft, ephemeral=ephemeral)
        for index, item in enumerate(points, start=1)
    ]
    total = _ephemeral_total(draft, points) if ephemeral else int(draft.total_minutes)
    status = _ephemeral_status(draft, points, total) if ephemeral else draft.route_status
    warnings = [RouteWarningRead(**item) for item in (draft.warnings or [])] + [
        RouteWarningRead(**item) for item in extra_warnings
    ]
    return RouteDraftRead(
        draft_id=draft.id,
        version=draft.version,
        route_status=status,
        total_minutes=total,
        budget_minutes=draft.budget_minutes,
        category_mode=draft.category_mode,
        selected_category_slugs=list(draft.selected_category_slugs or []),
        points=point_reads,
        warnings=warnings,
        category_summary=_summary(draft, points),
    )


def _point_read(
    item: RouteDraftPoint,
    position: int,
    *,
    points: list[RouteDraftPoint],
    draft: RouteDraft,
    ephemeral: bool,
) -> DraftPointRead:
    place = item.place
    walk_from, walk_to = item.walk_minutes_from_prev, item.walk_minutes_to_next
    if ephemeral:
        walk_from, walk_to = _recomputed_walks(draft, points, position - 1)
    return DraftPointRead(
        id=item.id,
        place_id=place.id,
        position=position,
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
        walk_minutes_from_prev=walk_from,
        walk_minutes_to_next=walk_to,
    )


def _recomputed_walks(
    draft: RouteDraft, points: list[RouteDraftPoint], index: int
) -> tuple[int | None, int | None]:
    current = points[index].place
    walk_from: int | None = None
    walk_to: int | None = None
    if index == 0 and draft.start_lat is not None and draft.start_lng is not None:
        walk_from = walk_minutes_between(
            float(draft.start_lat), float(draft.start_lng), float(current.lat), float(current.lng)
        )
    elif index > 0:
        prev = points[index - 1].place
        walk_from = walk_minutes_between(
            float(prev.lat), float(prev.lng), float(current.lat), float(current.lng)
        )
    if index + 1 < len(points):
        nxt = points[index + 1].place
        walk_to = walk_minutes_between(
            float(current.lat), float(current.lng), float(nxt.lat), float(nxt.lng)
        )
    return walk_from, walk_to


def _ephemeral_total(draft: RouteDraft, points: list[RouteDraftPoint]) -> int:
    visits = sum(int(point.visit_minutes or 0) for point in points)
    if not points:
        return visits
    walks = 0
    for index in range(len(points)):
        walk_from, _ = _recomputed_walks(draft, points, index)
        walks += int(walk_from or 0)
    return int(visits + walks)


def _ephemeral_status(draft: RouteDraft, points: list[RouteDraftPoint], total: int) -> str:
    if not points:
        return "no_route"
    if total > draft.budget_minutes or len(points) < 2:
        return "partial"
    return "full"


def _summary(draft: RouteDraft, points: list[RouteDraftPoint]) -> CategorySummaryRead:
    requested = list(draft.selected_category_slugs or [])
    counts = Counter(item.place.category for item in points if item.place.category)
    matched = {category: int(counts.get(category, 0)) for category in requested}
    neutral = sum(1 for item in points if item.place.category not in requested)
    missing = [category for category in requested if matched.get(category, 0) == 0]
    return CategorySummaryRead(requested=requested, matched=matched, neutral_added=neutral, missing=missing)
