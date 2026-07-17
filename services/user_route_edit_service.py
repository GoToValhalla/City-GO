from __future__ import annotations

from sqlalchemy.orm import Session

from models.city import City
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
from services.route_eligibility import apply_public_route_eligible_filters
from services.route_geometry import walk_minutes_between
from services.user_route_place_loader import load_ordered_places, load_place
from services.user_route_recalc_service import UserRouteRecalcService


class UserRouteEditService:
    def update_order(self, db: Session, request: UserRouteUpdateRequest) -> UserRouteState:
        places = _load_places_by_ids(db, request.ordered_place_ids)
        return UserRouteRecalcService().recalc(
            places=places,
            intent=request.current_route.context,
            revision=request.current_route.revision + 1,
            extra_warnings=["Порядок маршрута обновлён."],
        )

    def replace_place(self, db: Session, request: UserRouteReplacePlaceRequest) -> UserRouteState:
        places = load_ordered_places(db, request.current_route)
        replacement = load_place(db, request.new_place_id)
        if replacement is None:
            places = [place for place in places if str(place.id) != request.old_place_id]
            warning = "Новое место не найдено или не опубликовано. Старая точка удалена."
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
        places = load_ordered_places(db, request.current_route)
        place = load_place(db, request.place_id)
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
        current = next((point for point in route.points if point.place_id == place_id), None)
        if current is None:
            return UserRouteAlternativesResponse(route_id=route.route_id, place_id=place_id, options=[])
        used_ids = {point.place_id for point in route.points}
        query = db.query(Place).filter(Place.category == current.category)
        query = apply_public_route_eligible_filters(query)
        current_city_slug = getattr(current, "city_slug", None)
        if current_city_slug:
            query = query.filter(Place.city.has(City.slug == current_city_slug))
        query = query.filter(~Place.id.in_([int(item) for item in used_ids if item.isdigit()]))
        options = sorted(
            query.limit(30).all(),
            key=lambda place: walk_minutes_between(current.lat, current.lng, float(place.lat), float(place.lng)),
        )[:limit]
        return UserRouteAlternativesResponse(
            route_id=route.route_id,
            place_id=place_id,
            options=[_alternative_from_place(place, current.lat, current.lng) for place in options],
        )

    def structured_options(self, db: Session, request: UserRouteStructuredBuildRequest) -> UserRouteStructuredBuildResponse:
        lat, lng = _start_location(request)
        slots: list[UserRouteSlotOptions] = []
        for slot in request.slots:
            query = apply_public_route_eligible_filters(db.query(Place).filter(Place.category == slot.category))
            if request.city_id:
                query = query.filter(Place.city.has(City.slug == request.city_id))
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


def _load_places_by_ids(db: Session, ids: list[str]) -> list[Place]:
    numeric_ids = [int(item) for item in ids if item.isdigit()]
    if not numeric_ids:
        return []
    places = apply_public_route_eligible_filters(db.query(Place).filter(Place.id.in_(numeric_ids))).all()
    by_id = {int(place.id): place for place in places}
    return [by_id[item] for item in numeric_ids if item in by_id]


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
    return result if inserted else [*places, place]


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
