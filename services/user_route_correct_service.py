from __future__ import annotations

from sqlalchemy.orm import Session

from schemas.user_route import UserRouteCorrectRequest, UserRouteIntent, UserRouteState
from services.public_route_place_access import resolve_route_scope
from services.route_builder_service import RouteBuilderService
from services.user_route_context import merge_unique, to_request_context, with_updates
from services.user_route_correction_actions import corrected_places
from services.user_route_mapper import final_route_to_state
from services.user_route_place_loader import load_ordered_places
from services.user_route_recalc_service import UserRouteRecalcService


class UserRouteCorrectService:
    def correct(self, db: Session, request: UserRouteCorrectRequest) -> UserRouteState:
        scope = resolve_route_scope(db, request.current_route)
        places = load_ordered_places(db, request.current_route)
        if scope is None:
            return UserRouteRecalcService().recalc(
                places=[],
                intent=request.current_route.context,
                revision=request.current_route.revision + 1,
                extra_warnings=["Маршрут больше недоступен для изменения."],
            )
        if request.action == "avoid_category":
            return self._rebuild(db, request, places)
        return self._recalc_existing(db, request, places)

    def _recalc_existing(self, db: Session, request: UserRouteCorrectRequest, places: list) -> UserRouteState:
        next_places = corrected_places(db, request, places)
        intent = self._intent_for_request(request, places)
        return UserRouteRecalcService().recalc(
            places=next_places,
            intent=intent,
            revision=request.current_route.revision + 1,
        )

    def _rebuild(self, db: Session, request: UserRouteCorrectRequest, places: list) -> UserRouteState:
        intent = self._intent_for_request(request, places)
        final = RouteBuilderService().build_route(
            db=db,
            request=to_request_context(intent),
            profile=None,
        )
        return final_route_to_state(
            final,
            intent,
            revision=request.current_route.revision + 1,
            status="corrected",
        )

    def _intent_for_request(
        self,
        request: UserRouteCorrectRequest,
        places: list,
    ) -> UserRouteIntent:
        intent = request.current_route.context
        target = _place_by_id(places, request.target_place_id)
        target_category = getattr(target, "category", None) if target is not None else None
        avoided = [target_category] if request.action == "avoid_category" and isinstance(target_category, str) and target_category else []
        target_exclusion = [request.target_place_id] if request.action == "remove_place" and target is not None else []
        return with_updates(
            intent,
            lat=request.current_lat,
            lng=request.current_lng,
            time_budget_minutes=request.new_time_budget_minutes,
            avoided_categories=merge_unique(intent.avoided_categories, [*request.avoided_categories, *avoided]),
            excluded_place_ids=merge_unique(intent.excluded_place_ids, target_exclusion),
        )


def _place_by_id(places: list, place_id: str | None):
    return next((place for place in places if str(place.id) == str(place_id)), None)
