from __future__ import annotations

from sqlalchemy.orm import Session

from models.place import Place
from schemas.merged_context import MergedContext
from services.candidate_retrieval_service import CandidateRetrievalService


class ResilientCandidateRetrievalService(CandidateRetrievalService):
    """Candidate retrieval with controlled fallback for cities whose import scopes are not published yet."""

    MIN_USABLE_POOL = 20

    def get_candidates(self, db: Session, ctx: MergedContext) -> list[Place]:
        candidates = super().get_candidates(db, ctx)
        if len(candidates) >= self.MIN_USABLE_POOL:
            return candidates

        candidates = self._fallback_relaxed_scope(db, ctx)
        if len(candidates) >= self.MIN_USABLE_POOL:
            return self._post_process(db, candidates, ctx)

        candidates = self._fallback_citywide(db, ctx)
        return self._post_process(db, candidates, ctx) if candidates else []

    def _fallback_relaxed_scope(self, db: Session, ctx: MergedContext) -> list[Place]:
        original = self._query_places
        try:
            self._query_places = lambda db_arg, ctx_arg: _query_without_scope(original, db_arg, ctx_arg, use_radius=True)  # type: ignore[method-assign]
            return super()._fallback_expand_radius(db, ctx)
        finally:
            self._query_places = original  # type: ignore[method-assign]

    def _fallback_citywide(self, db: Session, ctx: MergedContext) -> list[Place]:
        original = self._query_places
        try:
            self._query_places = lambda db_arg, ctx_arg: _query_without_scope(original, db_arg, ctx_arg, use_radius=False)  # type: ignore[method-assign]
            return original(db, ctx)
        finally:
            self._query_places = original  # type: ignore[method-assign]

    def _post_process(self, db: Session, candidates: list[Place], ctx: MergedContext) -> list[Place]:
        with_images = self._safe_attach_public_images(db, candidates)
        ranked = self._pre_rank_candidates(with_images, ctx)
        balanced = __import__("services.candidate_category_budget", fromlist=["balance_candidates_by_category"]).balance_candidates_by_category(ranked, self.TARGET_CANDIDATES)
        return balanced or ranked or with_images or candidates


def _query_without_scope(original, db: Session, ctx: MergedContext, *, use_radius: bool) -> list[Place]:
    from sqlalchemy import case, func, literal, select
    from models.city import City
    from services.route_eligibility import route_eligible_sql_conditions

    lat, lng = ctx.location
    lat_delta = (func.radians(Place.lat) - func.radians(lat)) / 2
    lng_delta = (func.radians(Place.lng) - func.radians(lng)) / 2
    haversine = (
        func.pow(func.sin(lat_delta), 2)
        + func.cos(func.radians(lat)) * func.cos(func.radians(Place.lat)) * func.pow(func.sin(lng_delta), 2)
    )
    sqrt_haversine = func.sqrt(haversine)
    clamped = case((sqrt_haversine > 1, literal(1)), else_=sqrt_haversine)
    distance_expr = 2 * 6_371_000 * func.asin(clamped)

    query = select(Place).where(*route_eligible_sql_conditions())
    if use_radius:
        query = query.where(distance_expr <= int(ctx.radius_meters * 2.5))
    query = query.join(City).where(City.is_active.is_(True), City.launch_status == "published")
    if ctx.city_id:
        query = query.where(City.slug == str(ctx.city_id))
    if ctx.avoided_place_ids:
        query = query.where(~Place.id.in_(ctx.avoided_place_ids))
    if ctx.avoided_categories:
        query = query.where(~Place.category.in_(ctx.avoided_categories))
    return db.execute(query.order_by(distance_expr.asc()).limit(300)).scalars().all()
