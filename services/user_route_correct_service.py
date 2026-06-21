from __future__ import annotations

from sqlalchemy.orm import Session

from schemas.user_route import UserRouteCorrectRequest, UserRouteIntent, UserRouteState
from services.route_builder_service import RouteBuilderService
from services.user_route_correction_actions import corrected_places
from services.user_route_context import merge_unique, to_request_context, with_updates
from services.user_route_mapper import final_route_to_state
from services.user_route_place_loader import load_ordered_places, load_place
from services.user_route_recalc_service import UserRouteRecalcService


class UserRouteCorrectService:
    def correct(self, db: Session, request: UserRouteCorrectRequest) -> UserRouteState:
        if request.action == "avoid_category":
            return self._rebuild(db, request)
        return self._recalc_existing(db, request)

    def _recalc_existing(self, db: Session, request: UserRouteCorrectRequest) -> UserRouteState:
        places = load_ordered_places(db, request.current_route)
        places = corrected_places(db, request, places)
        intent = self._intent_for_request(db, request)
        return UserRouteRecalcService().recalc(
            places=places,
            intent=intent,
            revision=request.current_route.revision + 1,
        )

    def _rebuild(self, db: Session, request: UserRouteCorrectRequest) -> UserRouteState:
        intent = self._intent_for_request(db, request)
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
        db: Session,
        request: UserRouteCorrectRequest,
    ) -> UserRouteIntent:
        intent = request.current_route.context
        return with_updates(
            intent,
            lat=request.current_lat,
            lng=request.current_lng,
            time_budget_minutes=request.new_time_budget_minutes,
            avoided_categories=self._avoided_categories(db, request),
            excluded_place_ids=self._excluded_place_ids(request),
        )

    def _avoided_categories(self, db: Session, request: UserRouteCorrectRequest) -> list[str]:
        extra = request.avoided_categories
        target = self._target_category(db, request)
        return merge_unique(request.current_route.context.avoided_categories, [*extra, *target])

    def _excluded_place_ids(self, request: UserRouteCorrectRequest) -> list[str]:
        current = request.current_route.context.excluded_place_ids
        target = [request.target_place_id] if request.action == "remove_place" and request.target_place_id else []
        return merge_unique(current, target)

    def _target_category(self, db: Session, request: UserRouteCorrectRequest) -> list[str]:
        if request.action != "avoid_category":
            return []
        place = load_place(db, request.target_place_id)
        category = getattr(place, "category", None) if place is not None else None
        return [category] if isinstance(category, str) and category else []
