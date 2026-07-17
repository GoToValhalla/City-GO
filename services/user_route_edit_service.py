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
from services.user_route_place_loader import load_ordered_places
from services.user_route_recalc_service import UserRouteRecalcService


class UserRouteEditService:
    def update_order(self, db: Session, request: UserRouteUpdateRequest) -> UserRouteState:
        scope = resolve_route_scope(db, request.current_route)
        current_places = load_ordered_places(db, request.current_route)
        current_ids = [str(place.id) for place in current_places]
        requested_ids = list(request.ordered_place_ids)
        if scope is None or len(requested_ids) != len(current_ids) or len(set(requested_ids)) != len(requested_ids) or set(requested_ids) != set(current_ids):
            return _safe_failure(request.current_route, current_places, "Порядок не изменён: список точек не соответствует текущему маршруту.")
        places = load_public_route_places(db, requested_ids, scope=scope)
        if len(places) != len(requested_ids):
            return _safe_failure(request.current_route, current_places, "Порядок не изменён: маршрут больше недоступен для изменения.")
        return _recalc(request.current_route, places, "Порядок маршрута обновлён.")

    def replace_place(self, db: Session, request: UserRouteReplacePlaceRequest) -> UserRouteState:
        scope = resolve_route_scope(db, request.current_route)
        current_places = load_ordered_places(db, request.current_route)
        current_ids = [str(place.id) for place in current_places]
        if scope is None or request.old_place_id not in current_ids:
            return _safe_failure(request.current_route, current_places, "Замена не выполнена: исходная точка не принадлежит текущему маршруту.")
        if request.new_place_id != request.old_place_id and request.new_place_id in current_ids:
            return _safe_failure(request.current_route, current_places, "Замена не выполнена: эта точка уже есть в маршруте.")
        replacement = load_public_route_place(db, request.new_place_id, scope=scope)
        if replacement is None:
            return _safe_failure(request.current_route, current_places, "Новое место недоступно для текущего маршрута. Маршрут не изменён.")
        places = [replacement if str(place.id) == request.old_place_id else place for place in current_places]
        return _recalc(request.current_route, places, "Место заменено.")

    def add_place(self, db: Session, request: UserRouteAddPlaceRequest) -> UserRouteState:
        scope = resolve_route_scope(db, request.current_route)
        current_places = load_ordered_places(db, request.current_route)
        current_ids = [str(place.id) for place in current_places]
        if scope is None:
            return _safe_failure(request.current_route, current_places, "Место не добавлено: состояние маршрута недействительно.")
        if request.insert_after_place_id is not None and request.insert_after_place_id not in current_ids:
            return _safe_failure(request.current_route, current_places, "Место не добавлено: точка вставки не принадлежит маршруту.")
        if request.place_id in current_ids:
            return _safe_failure(request.current_route, current_places, "Место уже есть в маршруте.")
        place = load_public_route_place(db, request.place_id, scope=scope)
        if place is None:
            return _safe_failure(request.current_route, current_places, "Место недоступно для текущего маршрута.")
        next_places = _insert_place(current_places, place, request.insert_after_place_id)
        return _recalc(request.current_route, next_places, "Место добавлено в маршрут.")

    def alternatives(self, db: Session, route: UserRouteState, place_id: str, limit: int = 3) -> UserRouteAlternativesResponse:
        scope = resolve_route_scope(db, route)
        current_places = load_ordered_places(db, route)
        route_ids = [str(place.id) for place in current_places]
        if scope is None or place_id not in route_ids:
            return UserRouteAlternativesResponse(route_id=route.route_id, place_id=place_id, options=[])
        current = load_public_route_place(db, place_id, scope=scope)
        if current is None:
            return UserRouteAlternativesResponse(route_id=route.route_id, place_id=place_id, options=[])
        query = public_route_place_query(db, scope=scope).filter(
            Place.category == current.category,
            ~Place.id.in_([int(item) for item in route_ids]),
        )
        options = sorted(
            query.limit(30).all(),
            key=lambda place: walk_minutes_between(float(current.lat), float(current.lng), float(place.lat), float(place.lng)),
        )[:limit]
        return UserRouteAlternativesResponse(
            route_id=route.route_id,
            place_id=place_id,
            options=[_alternative_from_place(place, float(current.lat), float(current.lng)) for place in options],
        )

    def structured_options(self, db: Session, request: UserRouteStructuredBuildRequest) -> UserRouteStructuredBuildResponse:
        lat, lng = _start_location(request)
        scope = resolve_intent_scope(db, request)
        slots: list[UserRouteSlotOptions] = []
        for slot in request.slots:
            query = public_route_place_query(db, scope=scope).filter(Place.category == slot.category)
            places = sorted(
                query.limit(30).all(),
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


def _safe_failure(route: UserRouteState, places: list[Place], warning: str) -> UserRouteState:
    return _recalc(route, places, warning)


def _recalc(route: UserRouteState, places: list[Place], warning: str) -> UserRouteState:
    return UserRouteRecalcService().recalc(
        places=places,
        intent=route.context,
        revision=route.revision + 1,
        extra_warnings=[warning],
    )


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
