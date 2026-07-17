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
    apply_public_route_city_scope,
    load_public_route_place,
    load_public_route_places,
    resolve_intent_city_id,
    resolve_route_city_id,
)
from services.route_geometry import walk_minutes_between
from services.user_route_place_loader import load_ordered_places
from services.user_route_recalc_service import UserRouteRecalcService


class UserRouteEditService:
    def update_order(self, db: Session, request: UserRouteUpdateRequest) -> UserRouteState:
        city_id = resolve_route_city_id(db, request.current_route)
        current_places = load_ordered_places(db, request.current_route)
        current_ids = [str(place.id) for place in current_places]
        requested_ids = [item for item in request.ordered_place_ids if item.isdigit()]
        if city_id is None or len(requested_ids) != len(current_ids) or set(requested_ids) != set(current_ids):
            places = current_places
            warning = "Порядок не изменён: список точек не соответствует текущему маршруту."
        else:
            places = load_public_route_places(db, requested_ids, city_id=city_id)
            warning = "Порядок маршрута обновлён."
        return UserRouteRecalcService().recalc(
            places=places,
            intent=request.current_route.context,
            revision=request.current_route.revision + 1,
            extra_warnings=[warning],
        )

    def replace_place(self, db: Session, request: UserRouteReplacePlaceRequest) -> UserRouteState:
        city_id = resolve_route_city_id(db, request.current_route)
        places = load_ordered_places(db, request.current_route)
        replacement = load_public_route_place(db, request.new_place_id, city_id=city_id)
        if replacement is None:
            warning = "Новое место не найдено или не опубликовано. Маршрут не изменён."
        else:
            places = [replacement if str(place.id) == request.old_place_id else place for place in places]
            warning = "Место заменено."
        return UserRouteRecalcService().recalc(
            places=places,
            intent=request.current_route.context,
            revision=request.current_route.revision + 1,
            extra_warnings=[warning],
        )

    def add_place(self, db: Session, request: UserRouteAddPlaceRequest) -> UserRouteState:
        city_id = resolve_route_city_id(db, request.current_route)
        places = load_ordered_places(db, request.current_route)
        place = load_public_route_place(db, request.place_id, city_id=city_id)
        if place is None:
            return UserRouteRecalcService().recalc(
                places=places,
                intent=request.current_route.context,
                revision=request.current_route.revision + 1,
                extra_warnings=["Место не найдено или не опубликовано."],
            )
        next_places = _insert_place(places, place, request.insert_after_place_id)
        return UserRouteRecalcService().recalc(
            places=next_places,
            intent=request.current_route.context,
            revision=request.current_route.revision + 1,
            extra_warnings=["Место добавлено в маршрут."],
        )

    def alternatives(self, db: Session, route: UserRouteState, place_id: str, limit: int = 3) -> UserRouteAlternativesResponse:
        city_id = resolve_route_city_id(db, route)
        current = load_public_route_place(db, place_id, city_id=city_id)
        if current is None:
            return UserRouteAlternativesResponse(route_id=route.route_id, place_id=place_id, options=[])
        used_ids = {point.place_id for point in route.points}
        query = apply_public_route_city_scope(
            db.query(Place).filter(Place.category == current.category),
            city_id=city_id,
        )
        query = query.filter(~Place.id.in_([int(item) for item in used_ids if item.isdigit()]))
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
        city_id = resolve_intent_city_id(db, request)
        slots: list[UserRouteSlotOptions] = []
        for slot in request.slots:
            query = apply_public_route_city_scope(
                db.query(Place).filter(Place.category == slot.category),
                city_id=city_id,
            )
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


def _insert_place(places: list[Place], place: Place, insert_after_place_id: str | None) -> list[Place]:
    if str(place.id) in {str(item.id) for item in places}:
        return places
    if not insert_after_place_id:
        return [*places, place]
    result: list[Place] = []
    inserted = False
    for current in places:
        result.append(current)
        if str(current.id) == insert_after_place_id:
            result.append(place)
            inserted = True
    return result if inserted else places


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
