from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from models.category import Category
from models.city import City
from models.place import Place
from models.place_field_confidence import PlaceFieldConfidence
from models.place_schedule import PlaceSchedule
from models.route import Route
from models.route_place import RoutePlace
from telegram_bot.quality import category_code, is_hours_reliable, is_place_bot_visible, is_route_point_bot_eligible
from telegram_bot.schemas import BotCity, BotPlace, BotRoute, BotRoutePoint, Page
from telegram_bot.utils import haversine_meters

DEFAULT_LIMIT = 5
CATEGORY_GROUPS = {
    "sights": {"culture", "museum", "park", "walk", "viewpoint", "beach"},
    "food": {"food", "coffee", "cafe"},
    "coffee": {"coffee", "cafe"},
}
WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


class BotFacade:
    def __init__(self, db: Session):
        self.db = db

    def published_cities(self) -> list[BotCity]:
        rows = (
            self.db.query(City)
            .filter(City.is_active.is_(True), City.launch_status == "published")
            .order_by(City.name.asc())
            .all()
        )
        return [self._city(row) for row in rows]

    def city(self, slug: str | None) -> BotCity | None:
        if not slug:
            return None
        row = self.db.query(City).filter(City.slug == slug, City.is_active.is_(True), City.launch_status == "published").first()
        return self._city(row) if row is not None else None

    def city_by_text(self, value: str) -> BotCity | None:
        normalized = value.strip()
        if not normalized:
            return None
        row = (
            self.db.query(City)
            .filter(City.is_active.is_(True), City.launch_status == "published")
            .filter(or_(City.slug.ilike(normalized), City.name.ilike(normalized)))
            .first()
        )
        if row is None:
            pattern = f"%{normalized}%"
            row = (
                self.db.query(City)
                .filter(City.is_active.is_(True), City.launch_status == "published")
                .filter(or_(City.slug.ilike(pattern), City.name.ilike(pattern)))
                .order_by(City.name.asc())
                .first()
            )
        return self._city(row) if row is not None else None

    def routes(self, city_slug: str, page: int = 0, limit: int = DEFAULT_LIMIT) -> Page:
        city = self._city_row(city_slug)
        if city is None:
            return Page([], page, False)
        rows = (
            self.db.query(Route)
            .options(joinedload(Route.route_places).joinedload(RoutePlace.place))
            .filter(Route.city_id == city.id, Route.is_active.is_(True))
            .order_by(Route.title.asc())
            .all()
        )
        valid = [route for route in (self._route(row) for row in rows) if len(route.points) >= 2]
        start = page * limit
        return Page(valid[start:start + limit], page, len(valid) > start + limit)

    def route(self, route_id: int) -> BotRoute | None:
        row = (
            self.db.query(Route)
            .options(joinedload(Route.route_places).joinedload(RoutePlace.place))
            .filter(Route.id == route_id, Route.is_active.is_(True))
            .first()
        )
        if row is None:
            return None
        route = self._route(row)
        return route if len(route.points) >= 2 else None

    def places_by_category(self, city_slug: str, category_group: str, page: int = 0, limit: int = DEFAULT_LIMIT) -> Page:
        city = self._city_row(city_slug)
        if city is None:
            return Page([], page, False)
        categories = CATEGORY_GROUPS.get(category_group, {category_group})
        rows = (
            self.db.query(Place)
            .outerjoin(Category, Place.category_id == Category.id)
            .filter(Place.city_id == city.id)
            .filter(or_(Place.category.in_(tuple(categories)), Place.canonical_category.in_(tuple(categories)), Category.code.in_(tuple(categories))))
            .order_by(Place.title.asc())
            .all()
        )
        valid = [self._place(row) for row in rows if is_place_bot_visible(row)]
        start = page * limit
        return Page(valid[start:start + limit], page, len(valid) > start + limit)

    def place(self, place_id: int) -> BotPlace | None:
        row = self.db.query(Place).filter(Place.id == place_id).first()
        if row is None or not is_place_bot_visible(row):
            return None
        return self._place(row)

    def search_places(self, city_slug: str, query: str, page: int = 0, limit: int = DEFAULT_LIMIT) -> Page:
        city = self._city_row(city_slug)
        normalized = query.strip()
        if city is None or not normalized:
            return Page([], page, False)
        pattern = f"%{normalized}%"
        rows = (
            self.db.query(Place)
            .filter(Place.city_id == city.id)
            .filter(or_(Place.title.ilike(pattern), Place.address.ilike(pattern), Place.category.ilike(pattern)))
            .order_by(Place.title.asc())
            .all()
        )
        valid = [self._place(row) for row in rows if is_place_bot_visible(row)]
        start = page * limit
        return Page(valid[start:start + limit], page, len(valid) > start + limit)

    def nearby_places(self, city_slug: str, lat: float, lng: float, category: str | None = None, limit: int = 10) -> list[BotPlace]:
        city = self._city_row(city_slug)
        if city is None:
            return []
        query = self.db.query(Place).filter(Place.city_id == city.id)
        if category and category != "all":
            categories = CATEGORY_GROUPS.get(category, {category})
            query = query.filter(or_(Place.category.in_(tuple(categories)), Place.canonical_category.in_(tuple(categories))))
        results = []
        for row in query.all():
            if not is_place_bot_visible(row) or row.lat is None or row.lng is None:
                continue
            distance = haversine_meters(lat, lng, row.lat, row.lng)
            if distance <= 3_000:
                place = self._place(row, distance_m=distance)
                results.append(place)
        return sorted(results, key=lambda item: item.distance_m or 0)[:limit]

    def open_now(self, city_slug: str, page: int = 0, limit: int = DEFAULT_LIMIT) -> Page:
        city = self._city_row(city_slug)
        if city is None:
            return Page([], page, False)
        now = datetime.now(ZoneInfo(city.timezone))
        weekday = WEEKDAYS[now.weekday()]
        rows = (
            self.db.query(Place)
            .join(PlaceSchedule, Place.id == PlaceSchedule.place_id)
            .filter(Place.city_id == city.id)
            .filter(PlaceSchedule.weekday == weekday)
            .filter(PlaceSchedule.is_closed.is_(False))
            .all()
        )
        valid = []
        for row in rows:
            if not is_place_bot_visible(row):
                continue
            schedule = next((item for item in row.schedules if item.weekday == weekday), None)
            if schedule is None or schedule.open_time is None or schedule.close_time is None:
                continue
            confidence = self._field_confidence(row.id, "opening_hours")
            if not is_hours_reliable(confidence):
                continue
            if schedule.open_time <= now.time() <= schedule.close_time:
                valid.append(self._place(row, hours_override=f"до {schedule.close_time.strftime('%H:%M')}"))
        start = page * limit
        return Page(valid[start:start + limit], page, len(valid) > start + limit)

    def favorite_places(self, place_ids: list[int]) -> list[BotPlace]:
        if not place_ids:
            return []
        rows = self.db.query(Place).filter(Place.id.in_(place_ids)).all()
        return [self._place(row) for row in rows if is_place_bot_visible(row)]

    def favorite_routes(self, route_ids: list[int]) -> list[BotRoute]:
        if not route_ids:
            return []
        rows = (
            self.db.query(Route)
            .options(joinedload(Route.route_places).joinedload(RoutePlace.place))
            .filter(Route.id.in_(route_ids), Route.is_active.is_(True))
            .all()
        )
        return [route for route in (self._route(row) for row in rows) if len(route.points) >= 2]

    def _city_row(self, slug: str) -> City | None:
        return self.db.query(City).filter(City.slug == slug, City.is_active.is_(True), City.launch_status == "published").first()

    def _city(self, row: City) -> BotCity:
        rows = self.db.query(Place).filter(Place.city_id == row.id).all()
        count = sum(1 for place in rows if is_place_bot_visible(place))
        return BotCity(id=row.id, slug=row.slug, name=row.name, places_count=count)

    def _route(self, row: Route) -> BotRoute:
        points = []
        for link in sorted(row.route_places, key=lambda item: item.position):
            place = link.place
            if place is None or not is_route_point_bot_eligible(place):
                continue
            points.append(
                BotRoutePoint(
                    index=len(points),
                    place_id=place.id,
                    title=place.title,
                    category=category_code(place),
                    short_description=place.short_description,
                    address=place.address,
                    image_url=_safe_image_url(place.image_url),
                    lat=place.lat,
                    lng=place.lng,
                )
            )
        return BotRoute(row.id, row.title, row.short_description, row.duration_minutes, row.distance_km, points)

    def _place(self, row: Place, distance_m: int | None = None, hours_override: str | None = None) -> BotPlace:
        confidence = self._field_confidence(row.id, "opening_hours")
        return BotPlace(
            id=row.id,
            title=row.title,
            category=category_code(row),
            category_name=row.category_ref.name if row.category_ref else None,
            short_description=row.short_description,
            address=row.address,
            image_url=_safe_image_url(row.image_url),
            opening_hours_display=hours_override or _format_opening_hours(row.opening_hours),
            hours_reliable=is_hours_reliable(confidence),
            lat=row.lat,
            lng=row.lng,
            distance_m=distance_m,
        )

    def _field_confidence(self, place_id: int, field_name: str) -> PlaceFieldConfidence | None:
        return self.db.query(PlaceFieldConfidence).filter_by(place_id=place_id, field_name=field_name).first()


def _format_opening_hours(value: object) -> str | None:
    if isinstance(value, dict):
        display = value.get("display") or value.get("raw") or value.get("text")
        return str(display) if display else None
    if isinstance(value, str):
        return value
    return None


def _safe_image_url(value: str | None) -> str | None:
    if not value or not value.startswith(("http://", "https://")):
        return None
    lowered = value.lower()
    if "placeholder" in lowered or "no-photo" in lowered or "no_photo" in lowered:
        return None
    return value
