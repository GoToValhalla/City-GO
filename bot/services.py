from __future__ import annotations

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from bot.quality import category_code, is_hours_reliable, is_place_bot_visible, is_route_point_visible
from bot.schemas import BotCity, BotPlace, BotRoute, BotRoutePoint, PaginatedResult
from models.category import Category
from models.city import City
from models.place import Place
from models.place_field_confidence import PlaceFieldConfidence
from models.route import Route
from models.route_place import RoutePlace

DEFAULT_LIMIT = 5
CATEGORY_FILTERS = {
    "sights": {"culture", "museum", "park", "walk", "viewpoint", "beach"},
    "food": {"food", "coffee", "cafe"},
    "coffee": {"coffee", "cafe"},
}


class BotFacade:
    def __init__(self, db: Session):
        self.db = db

    def get_published_cities(self) -> list[BotCity]:
        rows = (
            self.db.query(City)
            .filter(City.is_active.is_(True), City.launch_status == "published")
            .order_by(City.name.asc())
            .all()
        )
        return [BotCity(id=row.id, slug=row.slug, name=row.name) for row in rows]

    def get_city(self, city_slug: str | None) -> BotCity | None:
        if not city_slug:
            return None
        row = self.db.query(City).filter(City.slug == city_slug, City.is_active.is_(True)).first()
        if row is None:
            return None
        return BotCity(id=row.id, slug=row.slug, name=row.name)

    def get_city_routes(self, city_slug: str, page: int = 0, limit: int = DEFAULT_LIMIT) -> PaginatedResult:
        city = self.db.query(City).filter(City.slug == city_slug).first()
        if city is None:
            return PaginatedResult(items=[], page=page, has_next=False)
        rows = (
            self.db.query(Route)
            .options(joinedload(Route.route_places).joinedload(RoutePlace.place))
            .filter(Route.city_id == city.id, Route.is_active.is_(True))
            .order_by(Route.title.asc())
            .offset(page * limit)
            .limit(limit + 1)
            .all()
        )
        routes = [route for route in (_to_route(row) for row in rows) if len(route.points) >= 2]
        return PaginatedResult(items=routes[:limit], page=page, has_next=len(routes) > limit)

    def get_route_detail(self, route_id: int) -> BotRoute | None:
        row = (
            self.db.query(Route)
            .options(joinedload(Route.route_places).joinedload(RoutePlace.place))
            .filter(Route.id == route_id, Route.is_active.is_(True))
            .first()
        )
        if row is None:
            return None
        route = _to_route(row)
        if len(route.points) < 2:
            return None
        return route

    def get_places_by_category(self, city_slug: str, category_group: str, page: int = 0, limit: int = DEFAULT_LIMIT) -> PaginatedResult:
        categories = CATEGORY_FILTERS.get(category_group, {category_group})
        city = self.db.query(City).filter(City.slug == city_slug).first()
        if city is None:
            return PaginatedResult(items=[], page=page, has_next=False)
        rows = (
            self.db.query(Place)
            .outerjoin(Category, Place.category_id == Category.id)
            .filter(Place.city_id == city.id)
            .filter(or_(Place.category.in_(tuple(categories)), Place.canonical_category.in_(tuple(categories)), Category.code.in_(tuple(categories))))
            .order_by(Place.title.asc())
            .offset(page * limit)
            .limit(limit + 1)
            .all()
        )
        places = [_to_place(row) for row in rows if is_place_bot_visible(row)]
        return PaginatedResult(items=places[:limit], page=page, has_next=len(places) > limit)

    def search_places(self, city_slug: str, query: str, page: int = 0, limit: int = DEFAULT_LIMIT) -> PaginatedResult:
        normalized = query.strip()
        if not normalized:
            return PaginatedResult(items=[], page=page, has_next=False)
        city = self.db.query(City).filter(City.slug == city_slug).first()
        if city is None:
            return PaginatedResult(items=[], page=page, has_next=False)
        pattern = f"%{normalized}%"
        rows = (
            self.db.query(Place)
            .filter(Place.city_id == city.id)
            .filter(or_(Place.title.ilike(pattern), Place.address.ilike(pattern), Place.category.ilike(pattern)))
            .order_by(Place.title.asc())
            .offset(page * limit)
            .limit(limit + 1)
            .all()
        )
        places = [_to_place(row) for row in rows if is_place_bot_visible(row)]
        return PaginatedResult(items=places[:limit], page=page, has_next=len(places) > limit)


def _to_route(route: Route) -> BotRoute:
    points: list[BotRoutePoint] = []
    for index, link in enumerate(sorted(route.route_places, key=lambda item: item.position)):
        place = link.place
        if place is None or not is_route_point_visible(place):
            continue
        points.append(
            BotRoutePoint(
                index=len(points),
                place_id=place.id,
                title=place.title,
                category=category_code(place),
                short_description=place.short_description,
                address=place.address,
                image_url=place.image_url,
                lat=place.lat,
                lng=place.lng,
            )
        )
    return BotRoute(
        id=route.id,
        title=route.title,
        short_description=route.short_description,
        duration_minutes=route.duration_minutes,
        distance_km=route.distance_km,
        points=points,
    )


def _to_place(place: Place) -> BotPlace:
    confidence = _field_confidence(place, "opening_hours")
    return BotPlace(
        id=place.id,
        title=place.title,
        category=category_code(place),
        category_name=place.category_ref.name if place.category_ref else None,
        short_description=place.short_description,
        address=place.address,
        image_url=place.image_url,
        opening_hours_display=_format_opening_hours(place.opening_hours),
        hours_reliable=is_hours_reliable(confidence),
        lat=place.lat,
        lng=place.lng,
    )


def _field_confidence(place: Place, field_name: str) -> PlaceFieldConfidence | None:
    for row in getattr(place, "field_confidence", []) or []:
        if row.field_name == field_name:
            return row
    return None


def _format_opening_hours(value: object) -> str | None:
    if isinstance(value, dict):
        display = value.get("display") or value.get("raw") or value.get("text")
        return str(display) if display else None
    if isinstance(value, str):
        return value
    return None
