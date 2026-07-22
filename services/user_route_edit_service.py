from __future__ import annotations

from sqlalchemy.orm import Session

from models.place import Place
from schemas.user_route import (
    UserRouteAddPlaceRequest,
    UserRouteAlternativePlace,
    UserRouteAlternativesResponse,
    UserRouteIntent,
    UserRouteReplacePlaceRequest,
    UserRouteState,
    UserRouteStructuredBuildRequest,
    UserRouteStructuredBuildResponse,
    UserRouteSlotOption,
    UserRouteSlotOptions,
    UserRouteUpdateRequest,
)
from services.public_route_place_access import (
    load_public_route_place,
    load_public_route_places,
    public_route_place_query,
    resolve_intent_scope,
    resolve_route_scope,
)
from services.route_geometry import walk_minutes_between
from services.user_route_mutation_result import RouteMutationResult
from services.user_route_place_loader import load_ordered_places
from services.user_route_recalc_service import UserRouteRecalcService
from services.feature_toggle_service import is_toggle_enabled
from services.routing_projection_candidate_service import (
    ROUTING_PROJECTION_TOGGLE,
    routing_projection_candidates,
    routing_projection_candidates_for_route,
)
from types import SimpleNamespace


class UserRouteEditService:
    def update_order(self, db: Session, request: UserRouteUpdateRequest) -> RouteMutationResult:
        current_places = load_ordered_places(db, request.current_route)
        projected = _projected_route_places(db, request.current_route)
        scope = None if projected is not None else resolve_route_scope(db, request.current_route)
        current_ids = [str(place.id) for place in current_places]
        requested_ids = list(request.ordered_place_ids)
        if (
            (scope is None and projected is None)
            or len(requested_ids) != len(current_ids)
            or len(set(requested_ids)) != len(requested_ids)
            or set(requested_ids) != set(current_ids)
        ):
            return RouteMutationResult.rejected(
                "Порядок не изменён: список точек не соответствует текущему маршруту."
            )
        if requested_ids == current_ids:
            return RouteMutationResult.rejected("Порядок точек уже совпадает с запрошенным.")
        places = (
            [_place_by_id(projected, place_id) for place_id in requested_ids]
            if projected is not None
            else load_public_route_places(db, requested_ids, scope=scope)
        )
        places = [place for place in places if place is not None]
        if len(places) != len(requested_ids):
            return RouteMutationResult.rejected(
                "Порядок не изменён: маршрут больше недоступен для изменения."
            )
        return _accepted_recalc(request.current_route, places, "Порядок маршрута обновлён.")

    def replace_place(self, db: Session, request: UserRouteReplacePlaceRequest) -> RouteMutationResult:
        current_places = load_ordered_places(db, request.current_route)
        projected = _projected_route_places(db, request.current_route)
        scope = None if projected is not None else resolve_route_scope(db, request.current_route)
        current_ids = [str(place.id) for place in current_places]
        if (scope is None and projected is None) or request.old_place_id not in current_ids:
            return RouteMutationResult.rejected(
                "Замена не выполнена: исходная точка не принадлежит текущему маршруту."
            )
        if request.new_place_id == request.old_place_id:
            return RouteMutationResult.rejected("Исходная и новая точки совпадают.")
        if request.new_place_id in current_ids:
            return RouteMutationResult.rejected(
                "Замена не выполнена: эта точка уже есть в маршруте."
            )
        replacement = _place_by_id(projected, request.new_place_id) if projected is not None else load_public_route_place(db, request.new_place_id, scope=scope)
        if replacement is None:
            return RouteMutationResult.rejected(
                "Новое место недоступно для текущего маршрута. Маршрут не изменён."
            )
        places = [replacement if str(place.id) == request.old_place_id else place for place in current_places]
        return _accepted_recalc(request.current_route, places, "Место заменено.")

    def add_place(self, db: Session, request: UserRouteAddPlaceRequest) -> RouteMutationResult:
        current_places = load_ordered_places(db, request.current_route)
        projected = _projected_route_places(db, request.current_route)
        scope = None if projected is not None else resolve_route_scope(db, request.current_route)
        current_ids = [str(place.id) for place in current_places]
        if scope is None and projected is None:
            return RouteMutationResult.rejected(
                "Место не добавлено: состояние маршрута недействительно."
            )
        if request.insert_after_place_id is not None and request.insert_after_place_id not in current_ids:
            return RouteMutationResult.rejected(
                "Место не добавлено: точка вставки не принадлежит маршруту."
            )
        if request.place_id in current_ids:
            return RouteMutationResult.rejected("Место уже есть в маршруте.")
        place = _place_by_id(projected, request.place_id) if projected is not None else load_public_route_place(db, request.place_id, scope=scope)
        if place is None:
            return RouteMutationResult.rejected(
                "Место недоступно для текущего маршрута."
            )
        next_places = _insert_place(current_places, place, request.insert_after_place_id)
        return _accepted_recalc(request.current_route, next_places, "Место добавлено в маршрут.")

    def alternatives(self, db: Session, route: UserRouteState, place_id: str, limit: int = 3) -> UserRouteAlternativesResponse:
        current_places = load_ordered_places(db, route)
        projected = _projected_route_places(db, route)
        scope = None if projected is not None else resolve_route_scope(db, route)
        route_ids = [str(place.id) for place in current_places]
        if (scope is None and projected is None) or place_id not in route_ids:
            return UserRouteAlternativesResponse(route_id=route.route_id, place_id=place_id, options=[])
        current = _place_by_id(projected, place_id) if projected is not None else load_public_route_place(db, place_id, scope=scope)
        if current is None:
            return UserRouteAlternativesResponse(route_id=route.route_id, place_id=place_id, options=[])
        candidates = (
            [place for place in projected or [] if place.category == current.category and str(place.id) not in route_ids]
            if projected is not None
            else public_route_place_query(db, scope=scope).filter(
                Place.category == current.category,
                ~Place.id.in_([int(item) for item in route_ids]),
            ).limit(30).all()
        )
        options = sorted(
            candidates,
            key=lambda place: walk_minutes_between(float(current.lat), float(current.lng), float(place.lat), float(place.lng)),
        )[:limit]
        return UserRouteAlternativesResponse(
            route_id=route.route_id,
            place_id=place_id,
            options=[_alternative_from_place(place, float(current.lat), float(current.lng)) for place in options],
        )

    def structured_options(self, db: Session, request: UserRouteStructuredBuildRequest) -> UserRouteStructuredBuildResponse:
        lat, lng = _start_location(request)
        projected = _projected_intent_places(db, request)
        scope = None if projected is not None else resolve_intent_scope(db, request)
        slots: list[UserRouteSlotOptions] = []
        for slot in request.slots:
            candidates = (
                [place for place in projected or [] if place.category == slot.category]
                if projected is not None
                else public_route_place_query(db, scope=scope).filter(Place.category == slot.category).limit(30).all()
            )
            places = sorted(
                candidates,
                key=lambda place: walk_minutes_between(lat, lng, float(place.lat), float(place.lng)),
            )[:3]
            slots.append(
                UserRouteSlotOptions(
                    slot_id=slot.slot_id,
                    category=slot.category,
                    options=[_slot_option(place, lat, lng) for place in places],
                )
            )
        return UserRouteStructuredBuildResponse(city_id=request.city_id, slots=slots)


def _accepted_recalc(route: UserRouteState, places: list[Place], warning: str) -> RouteMutationResult:
    state = UserRouteRecalcService().recalc(
        places=places,
        intent=route.context,
        revision=route.revision + 1,
        extra_warnings=[warning],
    )
    return RouteMutationResult.success(state)


def _insert_place(places: list[Place], place: Place, insert_after_place_id: str | None) -> list[Place]:
    if not insert_after_place_id:
        return [*places, place]
    result: list[Place] = []
    for current in places:
        result.append(current)
        if str(current.id) == insert_after_place_id:
            result.append(place)
    return result


def _alternative_from_place(place: Place, lat: float, lng: float) -> UserRouteAlternativePlace:
    return UserRouteAlternativePlace(
        place_id=str(place.id),
        city_slug=getattr(getattr(place, "city", None), "slug", None),
        title=place.title,
        address=place.address,
        image_url=place.image_url,
        category=place.category,
        score=float(getattr(place, "confidence", 0.0) or 0.0),
        walk_minutes=walk_minutes_between(lat, lng, float(place.lat), float(place.lng)),
    )


def _slot_option(place: Place, lat: float, lng: float) -> UserRouteSlotOption:
    return UserRouteSlotOption(
        place_id=str(place.id),
        title=place.title,
        address=place.address,
        image_url=place.image_url,
        category=str(place.category or ""),
        score=float(getattr(place, "confidence", 0.0) or 0.0),
        walk_minutes=walk_minutes_between(lat, lng, float(place.lat), float(place.lng)),
    )


def _start_location(intent: UserRouteIntent) -> tuple[float, float]:
    return float(intent.lat), float(intent.lng)


def _projected_route_places(db: Session, route: UserRouteState) -> list[Place] | None:
    if not is_toggle_enabled(db, ROUTING_PROJECTION_TOGGLE, default=False):
        return None
    return routing_projection_candidates_for_route(db, route)


def _place_by_id(places: list[Place] | None, place_id: str) -> Place | None:
    return next((place for place in places or [] if str(place.id) == place_id), None)


def _projected_intent_places(db: Session, intent: UserRouteIntent) -> list[Place] | None:
    if not is_toggle_enabled(db, ROUTING_PROJECTION_TOGGLE, default=False):
        return None
    return routing_projection_candidates(
        db,
        SimpleNamespace(
            city_id=intent.city_id,
            destination_id=getattr(intent, "destination_id", None),
            location=(intent.lat, intent.lng),
            radius_meters=0,
            avoided_place_ids=[],
            avoided_categories=[],
        ),
    )
