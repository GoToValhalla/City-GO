from __future__ import annotations

from sqlalchemy import case, func, literal, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from models.city import City
from models.place import Place
from schemas.merged_context import MergedContext
from services.candidate_category_budget import balance_candidates_by_category
from services.place_public_image_attach_service import attach_public_images
from services.route_eligibility import route_eligible_sql_conditions
from services.route_geometry import walk_minutes_between

ROUTE_FRIENDLY_CATEGORIES = frozenset(
    {
        "attraction",
        "culture",
        "gallery",
        "historic",
        "history",
        "landmark",
        "monument",
        "museum",
        "outdoor",
        "park",
        "promenade",
        "sightseeing",
        "viewpoint",
        "walk",
    }
)

FOOD_AND_REST_CATEGORIES = frozenset({"cafe", "coffee", "food", "restaurant", "bar", "pub"})

# Города в UI могут быть в статусе "готовится" / preview, но уже иметь публичные
# route-eligible места. Маршрутная сборка должна опираться на активность города и
# качество мест, а не блокироваться launch_status == published.
BLOCKED_CITY_LAUNCH_STATUSES = frozenset({"disabled", "archived", "hidden"})


class CandidateRetrievalService:
    MAX_CANDIDATES = 500
    TARGET_CANDIDATES = 180

    def get_candidates(
        self,
        db: Session,
        ctx: MergedContext,
    ) -> list[Place]:

        candidates = self._query_places(db, ctx)

        if len(candidates) < 20:
            candidates = self._fallback_expand_radius(db, ctx)

        if len(candidates) < 20:
            candidates = self._fallback_city_wide(db, ctx)

        if not candidates:
            return []

        with_images = self._safe_attach_public_images(db, candidates)
        ranked = self._pre_rank_candidates(with_images, ctx)
        balanced = balance_candidates_by_category(ranked, self.TARGET_CANDIDATES)

        # Защита от пустого маршрута после post-processing: SQL уже нашёл кандидатов,
        # поэтому ranking/balancing/image enrichment не имеют права обнулить пул.
        return balanced or ranked or with_images or candidates

    def _safe_attach_public_images(self, db: Session, candidates: list[Place]) -> list[Place]:
        try:
            return attach_public_images(db, candidates)
        except Exception:
            # Фото не должны ломать построение маршрута. Ошибка image enrichment деградирует
            # только качество карточек, но не должна превращать город с местами в no_route.
            return candidates

    def _query_places(
        self,
        db: Session,
        ctx: MergedContext,
    ) -> list[Place]:

        lat, lng = ctx.location

        distance_expr = self._distance_meters_expr(lat=lat, lng=lng)
        query = self._base_query(ctx).where(distance_expr <= ctx.radius_meters)
        query = query.order_by(distance_expr.asc()).limit(self.MAX_CANDIDATES)
        return db.execute(query).scalars().all()

    def _base_query(self, ctx: MergedContext):
        query = select(Place).where(*route_eligible_sql_conditions())
        query = query.join(City).where(
            City.is_active.is_(True),
            ~City.launch_status.in_(BLOCKED_CITY_LAUNCH_STATUSES),
        )
        if ctx.city_id:
            query = query.where(City.slug == str(ctx.city_id))

        # Важно: не фильтруем кандидатов по CityImportScope.status.
        # В проде импортные места могут быть связаны со scope в статусе completed/ready,
        # при этом сами места уже public + route_eligible. Старый _scope_is_route_visible()
        # превращал город с тысячами доступных мест в 0 кандидатов для маршрута.

        if ctx.avoided_place_ids:
            query = query.where(~Place.id.in_(ctx.avoided_place_ids))

        if ctx.avoided_categories:
            query = query.where(~Place.category.in_(ctx.avoided_categories))

        return query

    def _fallback_expand_radius(
        self,
        db: Session,
        ctx: MergedContext,
    ) -> list[Place]:

        expanded_ctx = ctx.model_copy(
            update={
                "radius_meters": max(12_000, int(ctx.radius_meters * 2.5)),
            },
        )

        return self._query_places(db, expanded_ctx)

    def _fallback_city_wide(
        self,
        db: Session,
        ctx: MergedContext,
    ) -> list[Place]:
        """Last retrieval fallback for active cities with usable data.

        If the selected start point is outside the dense part of the city or the city is spread
        wider than the walking radius, a strict radius query can return too few places even when
        the city has hundreds of route-eligible items. In that case we still return nearest usable
        city places, ordered by quality first and distance second downstream.
        """
        lat, lng = ctx.location
        distance_expr = self._distance_meters_expr(lat=lat, lng=lng)
        query = self._base_query(ctx).order_by(distance_expr.asc()).limit(self.MAX_CANDIDATES)
        return db.execute(query).scalars().all()

    def _pre_rank_candidates(self, candidates: list[Place], ctx: MergedContext) -> list[Place]:
        """Sort route candidates by stable data quality signals before category balancing.

        SQL retrieval still limits by radius and route eligibility. This step only reorders the
        loaded candidate pool so stronger tourist places are less likely to be cut by balancing.
        It intentionally does not use place title or any city-specific hardcode.
        """
        if not candidates:
            return []

        start_lat, start_lng = ctx.location
        return sorted(
            candidates,
            key=lambda place: (
                self._candidate_quality_score(place, start_lat, start_lng),
                -self._safe_place_id(place),
            ),
            reverse=True,
        )

    def _candidate_quality_score(self, place: Place, start_lat: float, start_lng: float) -> float:
        category = _category(place)
        score = 0.0

        if _has_image(place):
            score += 0.24
        if _has_address(place):
            score += 0.16
        if _has_description(place):
            score += 0.18
        if _has_opening_hours(place):
            score += 0.08
        if _has_quality_validation(place):
            score += 0.08
        if category in ROUTE_FRIENDLY_CATEGORIES:
            score += 0.18
        elif category in FOOD_AND_REST_CATEGORIES:
            score += 0.08

        score += self._distance_score(place, start_lat, start_lng) * 0.08
        return round(score, 5)

    def _distance_score(self, place: Place, start_lat: float, start_lng: float) -> float:
        lat = getattr(place, "lat", None)
        lng = getattr(place, "lng", None)
        if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
            return 0.0
        minutes = walk_minutes_between(start_lat, start_lng, float(lat), float(lng))
        if minutes <= 8:
            return 1.0
        if minutes <= 18:
            return 0.7
        if minutes <= 30:
            return 0.35
        return 0.1

    def _safe_place_id(self, place: Place) -> int:
        value = getattr(place, "id", 0) or 0
        return int(value) if isinstance(value, int) else 0

    def _distance_meters_expr(self, lat: float, lng: float) -> ColumnElement[float]:
        lat_delta = (func.radians(Place.lat) - func.radians(lat)) / 2
        lng_delta = (func.radians(Place.lng) - func.radians(lng)) / 2
        haversine = (
            func.pow(func.sin(lat_delta), 2)
            + func.cos(func.radians(lat))
            * func.cos(func.radians(Place.lat))
            * func.pow(func.sin(lng_delta), 2)
        )

        sqrt_haversine = func.sqrt(haversine)
        # SQLite не имеет LEAST(); CASE совместим с PostgreSQL и SQLite.
        clamped = case((sqrt_haversine > 1, literal(1)), else_=sqrt_haversine)
        return 2 * 6_371_000 * func.asin(clamped)


def _has_image(place: Place) -> bool:
    return bool(
        getattr(place, "image_url", None)
        or getattr(place, "public_image_url", None)
        or getattr(place, "primary_image_url", None)
        or getattr(place, "photo_url", None)
    )


def _has_address(place: Place) -> bool:
    return bool(str(getattr(place, "address", "") or "").strip())


def _has_description(place: Place) -> bool:
    return bool(
        str(getattr(place, "short_description", "") or "").strip()
        or str(getattr(place, "description", "") or "").strip()
    )


def _has_opening_hours(place: Place) -> bool:
    value = getattr(place, "opening_hours", None)
    if isinstance(value, dict):
        return bool(value)
    return bool(str(value or "").strip())


def _has_quality_validation(place: Place) -> bool:
    validation = getattr(place, "validation", None)
    if isinstance(validation, dict):
        return bool(validation.get("is_valid", True))
    quality_score = getattr(place, "quality_score", None)
    return isinstance(quality_score, (int, float)) and float(quality_score) >= 0.5


def _category(place: Place) -> str:
    return str(getattr(place, "category", "") or "").strip().casefold()
