from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

from sqlalchemy import case, func, literal, or_, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from models.city import City
from models.place import Place
from schemas.merged_context import MergedContext
from services.candidate_category_budget import balance_candidates_by_category
from services.place_public_image_attach_service import attach_public_images
from services.place_public_visibility import public_route_place_conditions
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
    MIN_HEALTHY_RETRIEVAL_CANDIDATES = 40
    LOW_COVERAGE_RATIO = 0.30

    def __init__(self) -> None:
        self.last_debug: dict[str, object] = {}

    def get_candidates(
        self,
        db: Session,
        ctx: MergedContext,
    ) -> list[Place]:

        density = self._safe_spatial_density(db, ctx)
        retrieval_counts = self._safe_retrieval_counts(db, ctx)
        city_wide_eligible = _safe_int(density.get("city_wide_eligible"))

        candidates = self._query_places(db, ctx)
        raw_candidates_count = len(candidates)
        expanded_candidates_count: int | None = None
        city_wide_candidates_count: int | None = None
        route_visible_candidates_count: int | None = None
        fallback_radius_used = False
        fallback_city_wide_used = False
        fallback_route_visible_used = False
        retrieval_strategy_used = "radius"

        if len(candidates) < self.MIN_HEALTHY_RETRIEVAL_CANDIDATES:
            expanded = self._fallback_expand_radius(db, ctx)
            expanded_candidates_count = len(expanded)
            fallback_radius_used = True
            if expanded:
                candidates = expanded
                retrieval_strategy_used = "expanded_radius"

        if self._needs_city_wide_fallback(candidates, city_wide_eligible):
            city_wide = self._fallback_city_wide(db, ctx)
            if isinstance(city_wide, list):
                city_wide_candidates_count = len(city_wide)
                if len(city_wide) > len(candidates):
                    candidates = city_wide
                    fallback_city_wide_used = True
                    retrieval_strategy_used = "city_wide_fallback"

        # Last safety net: production data may be visible and route-enabled for the UI, while
        # strict route eligibility SQL can still return zero because enrichment fields are
        # incomplete or stale. In that case we fallback to public route-visible places with
        # coordinates, preserving explicit user exclusions. This prevents "215 places -> 0
        # candidates" and lets downstream scoring/quality gates degrade honestly instead of
        # returning an empty route at retrieval.
        if not candidates and self._route_visible_data_exists(retrieval_counts):
            route_visible = self._fallback_route_visible_city_wide(db, ctx)
            route_visible_candidates_count = len(route_visible)
            if route_visible:
                candidates = route_visible
                fallback_route_visible_used = True
                retrieval_strategy_used = "route_visible_city_wide_fallback"

        if not candidates:
            self.last_debug = self._debug_payload(
                ctx,
                raw_candidates_count,
                [],
                fallback_radius_used,
                fallback_city_wide_used,
                fallback_route_visible_used=fallback_route_visible_used,
                density=density,
                retrieval_counts=retrieval_counts,
                expanded_candidates_count=expanded_candidates_count,
                city_wide_candidates_count=city_wide_candidates_count,
                route_visible_candidates_count=route_visible_candidates_count,
                retrieval_strategy_used="empty",
            )
            return []

        with_images = self._safe_attach_public_images(db, candidates)
        ranked = self._pre_rank_candidates(with_images, ctx)
        balanced = balance_candidates_by_category(ranked, self.TARGET_CANDIDATES)

        # Защита от пустого маршрута после post-processing: SQL уже нашёл кандидатов,
        # поэтому ranking/balancing/image enrichment не имеют права обнулить пул.
        final = balanced or ranked or with_images or candidates
        self.last_debug = self._debug_payload(
            ctx,
            raw_candidates_count,
            final,
            fallback_radius_used,
            fallback_city_wide_used,
            fallback_route_visible_used=fallback_route_visible_used,
            density=density,
            retrieval_counts=retrieval_counts,
            expanded_candidates_count=expanded_candidates_count,
            city_wide_candidates_count=city_wide_candidates_count,
            route_visible_candidates_count=route_visible_candidates_count,
            retrieval_strategy_used=retrieval_strategy_used,
        )
        return final

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

    def _base_query(self, ctx: MergedContext, *, apply_user_exclusions: bool = True):
        query = select(Place).where(*route_eligible_sql_conditions())
        query = query.join(City, Place.city_id == City.id).where(
            City.is_active.is_(True),
            ~City.launch_status.in_(BLOCKED_CITY_LAUNCH_STATUSES),
        )
        if ctx.city_id:
            query = query.where(City.slug == str(ctx.city_id))

        # Важно: не фильтруем кандидатов по CityImportScope.status.
        # В проде импортные места могут быть связаны со scope в статусе completed/ready,
        # при этом сами места уже public + route_eligible. Старый _scope_is_route_visible()
        # превращал город с тысячами доступных мест в 0 кандидатов для маршрута.

        if not apply_user_exclusions:
            return query

        return self._apply_user_exclusions(query, ctx)

    def _apply_user_exclusions(self, query, ctx: MergedContext):
        avoided_place_ids = list(getattr(ctx, "avoided_place_ids", []) or [])
        if avoided_place_ids:
            query = query.where(~Place.id.in_(avoided_place_ids))

        avoided_categories = _category_variants(getattr(ctx, "avoided_categories", []) or [])
        if avoided_categories:
            query = query.where(~func.lower(Place.category).in_(sorted(avoided_categories)))

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

    def _fallback_route_visible_city_wide(
        self,
        db: Session,
        ctx: MergedContext,
    ) -> list[Place]:
        """Fallback to route-visible public places when strict eligibility returns zero.

        This still keeps true hard constraints: active city, public route visibility,
        coordinates, and explicit user exclusions. It does not relax avoided categories or
        excluded place ids.
        """
        lat, lng = ctx.location
        distance_expr = self._distance_meters_expr(lat=lat, lng=lng)
        query = (
            select(Place)
            .join(City, Place.city_id == City.id)
            .where(
                City.is_active.is_(True),
                ~City.launch_status.in_(BLOCKED_CITY_LAUNCH_STATUSES),
                *public_route_place_conditions(),
                Place.lat.is_not(None),
                Place.lng.is_not(None),
            )
        )
        if ctx.city_id:
            query = query.where(City.slug == str(ctx.city_id))
        query = self._apply_user_exclusions(query, ctx)
        query = query.order_by(distance_expr.asc()).limit(self.MAX_CANDIDATES)
        return db.execute(query).scalars().all()

    def _needs_city_wide_fallback(self, candidates: list[Place], city_wide_eligible: int | None) -> bool:
        if not candidates:
            return True
        if len(candidates) < self.MIN_HEALTHY_RETRIEVAL_CANDIDATES:
            return True
        if city_wide_eligible and city_wide_eligible >= self.MIN_HEALTHY_RETRIEVAL_CANDIDATES:
            coverage = len(candidates) / city_wide_eligible
            return coverage < self.LOW_COVERAGE_RATIO
        return False

    def _route_visible_data_exists(self, retrieval_counts: dict[str, object]) -> bool:
        route_after = _safe_int(retrieval_counts.get("route_eligible_after_user_exclusions"))
        city_scope_total = _safe_int(retrieval_counts.get("city_scope_total"))
        return bool((route_after and route_after > 0) or (city_scope_total and city_scope_total > 0))

    def _safe_spatial_density(self, db: Session, ctx: MergedContext) -> dict[str, int | None]:
        try:
            return {
                "places_within_500m": self._count_places(db, ctx, 500),
                "places_within_1km": self._count_places(db, ctx, 1_000),
                "places_within_2km": self._count_places(db, ctx, 2_000),
                "places_within_5km": self._count_places(db, ctx, 5_000),
                "places_within_10km": self._count_places(db, ctx, 10_000),
                "city_wide_eligible": self._count_places(db, ctx, None),
            }
        except Exception:
            return {
                "places_within_500m": None,
                "places_within_1km": None,
                "places_within_2km": None,
                "places_within_5km": None,
                "places_within_10km": None,
                "city_wide_eligible": None,
            }

    def _safe_retrieval_counts(self, db: Session, ctx: MergedContext) -> dict[str, object]:
        """Return step-by-step retrieval counters for visible UI debugging.

        This intentionally duplicates a few cheap count queries because the route builder is in
        active stabilization. The goal is to see exactly whether candidates die in radius search,
        route eligibility, user exclusions, or post-processing.
        """
        try:
            radius = int(getattr(ctx, "radius_meters", 0) or 0)
            expanded_radius = max(12_000, int(radius * 2.5)) if radius else 12_000
            route_before_exclusions = self._count_places(db, ctx, None, apply_user_exclusions=False)
            route_after_exclusions = self._count_places(db, ctx, None, apply_user_exclusions=True)
            radius_before_exclusions = self._count_places(db, ctx, radius, apply_user_exclusions=False)
            radius_after_exclusions = self._count_places(db, ctx, radius, apply_user_exclusions=True)
            expanded_before_exclusions = self._count_places(db, ctx, expanded_radius, apply_user_exclusions=False)
            expanded_after_exclusions = self._count_places(db, ctx, expanded_radius, apply_user_exclusions=True)
            route_visible_city_wide = self._count_route_visible_places(db, ctx, None, apply_user_exclusions=True)
            route_visible_radius = self._count_route_visible_places(db, ctx, radius, apply_user_exclusions=True)
            return {
                "city_scope_total": self._count_city_scope_places(db, ctx),
                "route_eligible_before_user_exclusions": route_before_exclusions,
                "route_eligible_after_user_exclusions": route_after_exclusions,
                "route_visible_city_wide_after_user_exclusions": route_visible_city_wide,
                "route_visible_radius_after_user_exclusions": route_visible_radius,
                "radius_meters": radius,
                "radius_before_user_exclusions": radius_before_exclusions,
                "radius_after_user_exclusions": radius_after_exclusions,
                "expanded_radius_meters": expanded_radius,
                "expanded_radius_before_user_exclusions": expanded_before_exclusions,
                "expanded_radius_after_user_exclusions": expanded_after_exclusions,
                "city_wide_after_user_exclusions": route_after_exclusions,
                "lost_by_user_exclusions_city_wide": max(0, route_before_exclusions - route_after_exclusions),
                "lost_by_user_exclusions_radius": max(0, radius_before_exclusions - radius_after_exclusions),
                "applied_avoided_categories": sorted(_category_variants(getattr(ctx, "avoided_categories", []) or [])),
                "applied_avoided_place_ids_count": len(list(getattr(ctx, "avoided_place_ids", []) or [])),
            }
        except Exception as exc:
            return {"error": f"{type(exc).__name__}: {exc}"}

    def _count_city_scope_places(self, db: Session, ctx: MergedContext) -> int:
        query = select(func.count()).select_from(Place).join(City, Place.city_id == City.id).where(
            City.is_active.is_(True),
            ~City.launch_status.in_(BLOCKED_CITY_LAUNCH_STATUSES),
        )
        if ctx.city_id:
            query = query.where(City.slug == str(ctx.city_id))
        return int(db.execute(query).scalar() or 0)

    def _count_places(
        self,
        db: Session,
        ctx: MergedContext,
        max_distance_meters: int | None,
        *,
        apply_user_exclusions: bool = True,
    ) -> int:
        query = self._base_query(ctx, apply_user_exclusions=apply_user_exclusions)
        if max_distance_meters is not None:
            lat, lng = ctx.location
            query = query.where(self._distance_meters_expr(lat=lat, lng=lng) <= max_distance_meters)
        count_query = select(func.count()).select_from(query.subquery())
        return int(db.execute(count_query).scalar() or 0)

    def _count_route_visible_places(
        self,
        db: Session,
        ctx: MergedContext,
        max_distance_meters: int | None,
        *,
        apply_user_exclusions: bool = True,
    ) -> int:
        query = (
            select(Place)
            .join(City, Place.city_id == City.id)
            .where(
                City.is_active.is_(True),
                ~City.launch_status.in_(BLOCKED_CITY_LAUNCH_STATUSES),
                *public_route_place_conditions(),
                Place.lat.is_not(None),
                Place.lng.is_not(None),
            )
        )
        if ctx.city_id:
            query = query.where(City.slug == str(ctx.city_id))
        if apply_user_exclusions:
            query = self._apply_user_exclusions(query, ctx)
        if max_distance_meters is not None:
            lat, lng = ctx.location
            query = query.where(self._distance_meters_expr(lat=lat, lng=lng) <= max_distance_meters)
        count_query = select(func.count()).select_from(query.subquery())
        return int(db.execute(count_query).scalar() or 0)

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

    def _debug_payload(
        self,
        ctx: MergedContext,
        raw_candidates_count: int,
        candidates: list[Place],
        fallback_radius_used: bool,
        fallback_city_wide_used: bool,
        *,
        fallback_route_visible_used: bool = False,
        density: dict[str, int | None] | None = None,
        retrieval_counts: dict[str, object] | None = None,
        expanded_candidates_count: int | None = None,
        city_wide_candidates_count: int | None = None,
        route_visible_candidates_count: int | None = None,
        retrieval_strategy_used: str = "radius",
    ) -> dict[str, object]:
        lat, lng = ctx.location
        city_wide_eligible = _safe_int((density or {}).get("city_wide_eligible"))
        coverage_pct = round((len(candidates) / city_wide_eligible) * 100, 2) if city_wide_eligible else None
        counts = retrieval_counts or {}
        return {
            "query_limit": self.MAX_CANDIDATES,
            "healthy_min_candidates": self.MIN_HEALTHY_RETRIEVAL_CANDIDATES,
            "low_coverage_threshold_pct": int(self.LOW_COVERAGE_RATIO * 100),
            "retrieval_strategy_used": retrieval_strategy_used,
            "raw_candidates_count": raw_candidates_count,
            "after_radius_count": raw_candidates_count,
            "expanded_radius_candidates_count": expanded_candidates_count,
            "city_wide_candidates_count": city_wide_candidates_count,
            "route_visible_candidates_count": route_visible_candidates_count,
            "final_candidates_count": len(candidates),
            "retrieval_coverage_pct": coverage_pct,
            "fallback_radius_used": fallback_radius_used,
            "fallback_city_wide_used": fallback_city_wide_used,
            "fallback_route_visible_used": fallback_route_visible_used,
            "center_used": {"lat": lat, "lng": lng},
            "spatial_density": density or {},
            "retrieval_counts": counts,
            "city_scope_total": counts.get("city_scope_total"),
            "route_eligible_before_user_exclusions": counts.get("route_eligible_before_user_exclusions"),
            "route_eligible_after_user_exclusions": counts.get("route_eligible_after_user_exclusions"),
            "route_visible_city_wide_after_user_exclusions": counts.get("route_visible_city_wide_after_user_exclusions"),
            "route_visible_radius_after_user_exclusions": counts.get("route_visible_radius_after_user_exclusions"),
            "radius_before_user_exclusions": counts.get("radius_before_user_exclusions"),
            "radius_after_user_exclusions": counts.get("radius_after_user_exclusions"),
            "expanded_radius_meters": counts.get("expanded_radius_meters"),
            "expanded_radius_before_user_exclusions": counts.get("expanded_radius_before_user_exclusions"),
            "expanded_radius_after_user_exclusions": counts.get("expanded_radius_after_user_exclusions"),
            "city_wide_after_user_exclusions": counts.get("city_wide_after_user_exclusions"),
            "lost_by_user_exclusions_city_wide": counts.get("lost_by_user_exclusions_city_wide"),
            "lost_by_user_exclusions_radius": counts.get("lost_by_user_exclusions_radius"),
            "applied_avoided_categories": counts.get("applied_avoided_categories"),
            "applied_avoided_place_ids_count": counts.get("applied_avoided_place_ids_count"),
            "retrieval_loss_summary": _retrieval_loss_summary(raw_candidates_count, len(candidates), city_wide_eligible, counts),
            "final_candidate_categories": _category_count_map(candidates),
            "places_within_500m": (density or {}).get("places_within_500m"),
            "places_within_1km": (density or {}).get("places_within_1km"),
            "places_within_2km": (density or {}).get("places_within_2km"),
            "places_within_5km": (density or {}).get("places_within_5km"),
            "places_within_10km": (density or {}).get("places_within_10km"),
            "city_wide_eligible": city_wide_eligible,
            "top_candidate_distances_meters": [
                _distance_meters(lat, lng, float(place.lat), float(place.lng))
                for place in candidates[:10]
                if _has_number_coords(place)
            ],
            "sample_candidate_ids": [str(getattr(place, "id", "")) for place in candidates[:10]],
            "sample_candidates": [_candidate_debug_row(place, lat, lng) for place in candidates[:10]],
        }

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


def _category_variants(categories: object) -> set[str]:
    variants: set[str] = set()
    for value in list(categories or []):
        raw = str(value or "").strip().casefold()
        if not raw:
            continue
        variants.add(raw)
        if raw.endswith("s") and raw not in {"bus", "gas"}:
            variants.add(raw[:-1])
        else:
            variants.add(f"{raw}s")
    return variants


def _safe_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _has_number_coords(place: object) -> bool:
    return isinstance(getattr(place, "lat", None), (int, float)) and isinstance(getattr(place, "lng", None), (int, float))


def _distance_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> int:
    lat_delta = (radians(lat2) - radians(lat1)) / 2
    lng_delta = (radians(lng2) - radians(lng1)) / 2
    value = sin(lat_delta) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(lng_delta) ** 2
    return int(round(2 * 6_371_000 * asin(min(1.0, sqrt(value)))))


def _category_count_map(candidates: list[Place]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for place in candidates:
        category = _category(place) or "unknown"
        counts[category] = counts.get(category, 0) + 1
    return dict(sorted(counts.items(), key=lambda item: item[1], reverse=True)[:20])


def _candidate_debug_row(place: Place, start_lat: float, start_lng: float) -> dict[str, object]:
    lat = getattr(place, "lat", None)
    lng = getattr(place, "lng", None)
    return {
        "id": str(getattr(place, "id", "") or ""),
        "name": str(getattr(place, "title", None) or getattr(place, "name", None) or ""),
        "category": _category(place),
        "lat": lat,
        "lng": lng,
        "distance_meters": _distance_meters(start_lat, start_lng, float(lat), float(lng)) if _has_number_coords(place) else None,
    }


def _retrieval_loss_summary(
    raw_candidates_count: int,
    final_candidates_count: int,
    city_wide_eligible: int | None,
    counts: dict[str, object],
) -> dict[str, object]:
    route_after = _safe_int(counts.get("route_eligible_after_user_exclusions"))
    route_visible_after = _safe_int(counts.get("route_visible_city_wide_after_user_exclusions"))
    radius_after = _safe_int(counts.get("radius_after_user_exclusions"))
    route_visible_radius_after = _safe_int(counts.get("route_visible_radius_after_user_exclusions"))
    expanded_after = _safe_int(counts.get("expanded_radius_after_user_exclusions"))
    return {
        "city_wide_eligible": city_wide_eligible,
        "route_eligible_after_user_exclusions": route_after,
        "route_visible_city_wide_after_user_exclusions": route_visible_after,
        "radius_after_user_exclusions": radius_after,
        "route_visible_radius_after_user_exclusions": route_visible_radius_after,
        "expanded_radius_after_user_exclusions": expanded_after,
        "raw_radius_candidates": raw_candidates_count,
        "final_candidates": final_candidates_count,
        "lost_before_radius": max(0, (route_after or 0) - (radius_after or 0)) if route_after is not None and radius_after is not None else None,
        "lost_after_post_processing": max(0, raw_candidates_count - final_candidates_count),
        "coverage_pct": round((final_candidates_count / city_wide_eligible) * 100, 2) if city_wide_eligible else None,
    }
