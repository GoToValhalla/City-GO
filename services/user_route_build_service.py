from __future__ import annotations

import time

from sqlalchemy.orm import Session

from models.city import City
from schemas.user_route import UserRouteBuildRequest, UserRouteState
from services.geocoding_service import GeocodingService
from services.route_builder_service import RouteBuilderService
from services.route_builder_v2_service import (
    apply_route_builder_v2_plan_to_intent,
    attach_route_builder_v2_result,
    build_route_builder_v2_plan_from_intent,
)
from services.user_profile_from_signals_service import build_user_profile_from_signals
from services.user_route_context import to_request_context
from services.destination_route_resolution import resolve_route_build_request
from services.user_route_mapper import final_route_to_state
from services.user_route_slot_build_service import UserRouteSlotBuildService

# Hard wall-clock cap for one build()/preview() call. Candidate retrieval is
# already bounded (CandidateRetrievalService.MAX_CANDIDATES=500) and the
# scoring/assembly pipeline is pure in-memory computation with no external
# calls, so this is defensive insurance against a pathological slow path
# causing an nginx 502 rather than a fix for a proven hang.
MAX_BUILD_SECONDS = 20


class RouteBuildTimeoutError(RuntimeError):
    """Raised when a single build()/preview() call exceeds MAX_BUILD_SECONDS."""


class UserRouteBuildService:
    """Построение пользовательского маршрута с подготовкой стартового контекста."""

    def build(self, db: Session, request: UserRouteBuildRequest) -> UserRouteState:
        deadline = time.monotonic() + MAX_BUILD_SECONDS
        resolved_request, _block = resolve_route_build_request(db, request)
        resolved_request = self._resolve_start_context(db, resolved_request)
        self._check_deadline(deadline)
        route_builder_plan = build_route_builder_v2_plan_from_intent(resolved_request)
        if route_builder_plan.mode == "slot":
            state = UserRouteSlotBuildService().build(db, resolved_request)
            self._check_deadline(deadline)
            attached = attach_route_builder_v2_result(state, route_builder_plan)
            if state.partial_reason and attached.partial_reason == "route_builder_v2_insufficient_points":
                return attached.model_copy(update={"partial_reason": state.partial_reason})
            return attached
        execution_request = apply_route_builder_v2_plan_to_intent(resolved_request, route_builder_plan)
        final = RouteBuilderService().build_route(
            db=db,
            request=to_request_context(execution_request),
            profile=build_user_profile_from_signals(db, execution_request.user_id),
        )
        self._check_deadline(deadline)
        state = final_route_to_state(final, execution_request, revision=1, status="ready")
        return attach_route_builder_v2_result(state, route_builder_plan)

    def _check_deadline(self, deadline: float) -> None:
        if time.monotonic() >= deadline:
            raise RouteBuildTimeoutError(f"Route build exceeded {MAX_BUILD_SECONDS}s deadline")

    def _resolve_start_context(self, db: Session, request: UserRouteBuildRequest) -> UserRouteBuildRequest:
        # Если пользователь ввёл адрес, пробуем получить координаты через Geoapify.
        # Если ключа нет или провайдер не вернул точку, остаёмся на координатах клиента.
        start_address = (request.start_address or "").strip()
        if not start_address:
            return request

        city_name = self._city_name(db, request.city_id)
        point = GeocodingService().geocode(start_address, city_name)
        if point is None:
            return request

        return request.model_copy(
            update={
                "lat": point.lat,
                "lng": point.lng,
                "start_source": "geocoded_address",
                "start_address": point.formatted_address or start_address,
            }
        )

    def _city_name(self, db: Session, city_slug: str | None) -> str | None:
        if not city_slug:
            return None
        city = db.query(City).filter(City.slug == city_slug).first()
        return city.name if city else city_slug
