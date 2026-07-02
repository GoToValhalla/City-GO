from __future__ import annotations

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
from services.user_route_mapper import final_route_to_state


class UserRouteBuildService:
    """Построение пользовательского маршрута с подготовкой стартового контекста."""

    def build(self, db: Session, request: UserRouteBuildRequest) -> UserRouteState:
        resolved_request = self._resolve_start_context(db, request)
        route_builder_plan = build_route_builder_v2_plan_from_intent(resolved_request)
        execution_request = apply_route_builder_v2_plan_to_intent(resolved_request, route_builder_plan)
        final = RouteBuilderService().build_route(
            db=db,
            request=to_request_context(execution_request),
            profile=build_user_profile_from_signals(db, execution_request.user_id),
        )
        state = final_route_to_state(final, execution_request, revision=1, status="ready")
        return attach_route_builder_v2_result(state, route_builder_plan)

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
