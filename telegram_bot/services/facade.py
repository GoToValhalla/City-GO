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
from services.city_service import get_available_cities
from telegram_bot.quality import category_code, is_hours_reliable, is_place_bot_visible, is_route_point_bot_eligible
from telegram_bot.schemas import BotCity, BotPlace, BotRoute, BotRoutePoint, Page
from telegram_bot.utils import haversine_meters
from services.catalog_projection_read_service import CATALOG_PROJECTION_TOGGLE, get_catalog_place, list_catalog_places
from services.feature_toggle_service import is_toggle_enabled
from services.search_projection_read_service import SEARCH_PROJECTION_TOGGLE, search_public_places_via_projection
from services.routing_projection_candidate_service import ROUTING_PROJECTION_TOGGLE, routing_projection_candidates
from types import SimpleNamespace

DEFAULT_LIMIT = 5
CATEGORY_GROUPS = {
    "all": set(),
    "sights": {"culture", "museum", "park", "walk", "viewpoint", "beach", "attraction", "landmark", "historic", "monument", "art", "architecture"},
    "food": {"food", "coffee", "cafe", "restaurant", "bar", "bakery", "fast_food", "ice_cream"},
    "coffee": {"coffee", "cafe"},
    "cafe": {"coffee", "cafe"},
    "park": {"park", "walk", "viewpoint", "beach"},
    "museum": {"museum", "culture", "art", "historic"},
}
WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")


def _public_available_cities(db: Session) -> list[dict[str, object]]:
    return get_available_cities(db)


class BotFacade:
    def __init__(self, db: Session):
        self.db = db

    def published_cities(self) -> list[BotCity]:
        return [self._city_from_available(row) for row in _public_available_cities(self.db)]

    def city(self, slug: str | None) -> BotCity | None:
        if not slug:
            return None
        for row in _public_available_cities(self.db):
            if row["slug"] == slug:
                return self._city_from_available(row)
        return None

    def city_by_text(self, value: str) -> BotCity | None:
        normalized = value.strip().lower()
        if not normalized:
            return None
        cities = _public_available_cities(self.db)
        for row in cities:
            if str(row["slug"]).lower() == normalized or str(row["name"]).lower() == normalized:
                return self._city_from_available(row)
        for row in cities:
            if normalized in str(row["slug"]).lower() or normalized in str(row["name"]).lower():
                return self._city_from_available(row)
        return None

    def city_center(self, city_slug: str) -> tuple[float, float] | None:
        city = self._city_row(city_slug)
        if city is None or city.center_lat is None or city.center_lng is None:
            return None
        return float(city.center_lat), float(city.center_lng)

    def routes(self, city_slug: str, page: int = 0, limit: int = DEFAULT_LIMIT) -> Page:
        city = self._city_row(city_slug)
        if city is None:
            return Page([], page, False)
        rows = (
            self.db.query(Route)
            .options(joinedload(Route.route_places).joinedload(RoutePlace.place).joinedload(Place.category_ref))
            .filter(Route.city_id == city.id, Route.is_active.is_(True))
            .order_by(Route.title.asc())
            .all()
        )
        valid = [route for route in (self._route(row) for row in rows) if len(route.points) >= 2]
        start = page * limit
        return Page(valid[start:start + limit], page, len(valid) > start + limit)

    def generated_route(self, city_slug: str, limit: int = 5) -> BotRoute | None:
        city = self._city_row(city_slug)
        if city is None:
            return None
        rows = self._projected_route_rows(city, limit) if is_toggle_enabled(self.db, ROUTING_PROJECTION_TOGGLE, default=False) else self._route_candidate_rows(city, limit)
        if len(rows) < 2:
            return None
        points = [
            BotRoutePoint(
                index=index,
                place_id=row.id,
                title=row.title,
                category=category_code(row),
                short_description=row.short_description,
                address=row.address,
                image_url=_safe_image_url(row.image_url),
                lat=row.lat,
                lng=row.lng,
            )
            for index, row in enumerate(rows)
        ]
        distance_km = _points_distance_km(points)
        walking_minutes = int((distance_km / 4.5) * 60) if distance_km else 0
        duration_minutes = max(30, walking_minutes + len(points) * 10)
        return BotRoute(
            id=0,
            title=f"Прогулка по {city.name}",
            short_description="Временный маршрут из опубликованных точек города. Можно пройти его прямо в Telegram.",
            duration_minutes=duration_minutes,
            distance_km=round(distance_km, 1) if distance_km else None,
            points=points,
        )

    def route(self, route_id: int) -> BotRoute | None:
        row = (
            self.db.query(Route)
            .options(joinedload(Route.route_places).joinedload(RoutePlace.place).joinedload(Place.category_ref))
            .filter(Route.id == route_id, Route.is_active.is_(True))
            .first()
        )
        if row is None or not self._city_is_public(row.city_id):
            return None
        route = self._route(row)
        return route if len(route.points) >= 2 else None

    def places_by_category(self, city_slug: str, category_group: str, page: int = 0, limit: int = DEFAULT_LIMIT) -> Page:
        if is_toggle_enabled(self.db, CATALOG_PROJECTION_TOGGLE, default=False):
            items, _ = list_catalog_places(self.db, city_slug=city_slug, limit=10_000)
            categories = CATEGORY_GROUPS.get(category_group, {category_group})
            rows = [_bot_place_from_public(row) for row in items if not categories or row.category in categories]
            start = page * limit
            return Page(rows[start:start + limit], page, len(rows) > start + limit)
        city = self._city_row(city_slug)
        if city is None:
            return Page([], page, False)
        query = self.db.query(Place).options(joinedload(Place.category_ref)).outerjoin(Category, Place.category_id == Category.id).filter(Place.city_id == city.id)
        categories = CATEGORY_GROUPS.get(category_group, {category_group})
        if categories:
            query = query.filter(or_(Place.category.in_(tuple(categories)), Place.canonical_category.in_(tuple(categories)), Category.code.in_(tuple(categories))))
        rows = query.order_by(Place.title.asc()).all()
        valid = [self._place(row) for row in rows if is_place_bot_visible(row)]
        start = page * limit
        return Page(valid[start:start + limit], page, len(valid) > start + limit)

    def place(self, place_id: int) -> BotPlace | None:
        if is_toggle_enabled(self.db, CATALOG_PROJECTION_TOGGLE, default=False):
            row = get_catalog_place(self.db, place_id=place_id)
            return _bot_place_from_public(row) if row else None
        row = self.db.query(Place).options(joinedload(Place.category_ref)).filter(Place.id == place_id).first()
        if row is None or not self._public_place(row):
            return None
        return self._place(row)

    def search_places(self, city_slug: str, query: str, page: int = 0, limit: int = DEFAULT_LIMIT) -> Page:
        if is_toggle_enabled(self.db, SEARCH_PROJECTION_TOGGLE, default=False):
            rows, total = search_public_places_via_projection(self.db, q=query, city_slug=city_slug, limit=limit, offset=page * limit)
            return Page([_bot_place_from_public(row) for row in rows], page, total > (page + 1) * limit)
        city = self._city_row(city_slug)
        normalized = query.strip()
        if city is None or not normalized:
            return Page([], page, False)
        pattern = f"%{normalized}%"
        rows = (
            self.db.query(Place)
            .options(joinedload(Place.category_ref))
            .outerjoin(Category, Place.category_id == Category.id)
            .filter(Place.city_id == city.id)
            .filter(or_(Place.title.ilike(pattern), Place.address.ilike(pattern), Place.category.ilike(pattern), Place.canonical_category.ilike(pattern), Category.name.ilike(pattern), Category.code.ilike(pattern)))
            .order_by(Place.title.asc())
            .all()
        )
        valid = [self._place(row) for row in rows if is_place_bot_visible(row)]
        start = page * limit
        return Page(valid[start:start + limit], page, len(valid) > start + limit)

    def nearby_places(self, city_slug: str, lat: float, lng: float, category: str | None = None, limit: int = 10) -> list[BotPlace]:
        if is_toggle_enabled(self.db, CATALOG_PROJECTION_TOGGLE, default=False):
            rows, _ = list_catalog_places(self.db, city_slug=city_slug, limit=10_000)
            categories = CATEGORY_GROUPS.get(category, {category}) if category and category != "all" else set()
            projected = [_bot_place_from_public(row, distance_m=int(haversine_meters(lat, lng, row.lat, row.lng))) for row in rows if row.lat is not None and row.lng is not None and (not categories or row.category in categories)]
            return sorted([row for row in projected if (row.distance_m or 0) <= 3_000], key=lambda row: row.distance_m or 0)[:limit]
        city = self._city_row(city_slug)
        if city is None:
            return []
        query = self.db.query(Place).options(joinedload(Place.category_ref)).filter(Place.city_id == city.id)
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
            .options(joinedload(Place.category_ref))
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

    def reliable_hours_places(self, city_slug: str, page: int = 0, limit: int = DEFAULT_LIMIT) -> Page:
        city = self._city_row(city_slug)
        if city is None:
            return Page([], page, False)
        rows = (
            self.db.query(Place)
            .options(joinedload(Place.category_ref))
            .filter(Place.city_id == city.id)
            .order_by(Place.quality_score.desc(), Place.title.asc())
            .all()
        )
        valid = []
        for row in rows:
            if not is_place_bot_visible(row) or not _format_opening_hours(row.opening_hours):
                continue
            if is_hours_reliable(self._field_confidence(row.id, "opening_hours")):
                valid.append(self._place(row))
        start = page * limit
        return Page(valid[start:start + limit], page, len(valid) > start + limit)

    def favorite_places(self, place_ids: list[int]) -> list[BotPlace]:
        if not place_ids:
            return []
        rows = self.db.query(Place).options(joinedload(Place.category_ref)).filter(Place.id.in_(place_ids)).all()
        return [self._place(row) for row in rows if self._public_place(row)]

    def favorite_routes(self, route_ids: list[int]) -> list[BotRoute]:
        if not route_ids:
            return []
        rows = (
            self.db.query(Route)
            .options(joinedload(Route.route_places).joinedload(RoutePlace.place).joinedload(Place.category_ref))
            .filter(Route.id.in_(route_ids), Route.is_active.is_(True))
            .all()
        )
        return [route for route in (self._route(row) for row in rows) if len(route.points) >= 2]

    def _city_is_public(self, city_id: int) -> bool:
        return (
            self.db.query(City.id)
            .filter(City.id == city_id, City.is_active.is_(True), City.launch_status == "published")
            .first()
            is not None
        )

    def _public_place(self, place: Place) -> bool:
        return self._city_is_public(place.city_id) and is_place_bot_visible(place)

    def _city_row(self, slug: str) -> City | None:
        if self.city(slug) is None:
            return None
        return self.db.query(City).filter(City.slug == slug, City.is_active.is_(True)).first()

    def _city_from_available(self, row: dict[str, object]) -> BotCity:
        return BotCity(
            id=0,
            slug=str(row["slug"]),
            name=str(row["name"]),
            places_count=int(row.get("places_count") or 0),
        )

    def _route_candidate_rows(self, city: City, limit: int) -> list[Place]:
        rows = (
            self.db.query(Place)
            .options(joinedload(Place.category_ref))
            .filter(Place.city_id == city.id)
            .filter(Place.lat.isnot(None), Place.lng.isnot(None), Place.is_route_eligible.is_(True))
            .order_by(Place.quality_score.desc(), Place.title.asc())
            .all()
        )
        visible = [row for row in rows if is_route_point_bot_eligible(row)]
        if city.center_lat is not None and city.center_lng is not None:
            visible = sorted(visible, key=lambda row: haversine_meters(float(city.center_lat), float(city.center_lng), row.lat, row.lng))

        selected = []
        seen_categories = set()
        for row in visible:
            code = category_code(row)
            if len(selected) < 2 or code not in seen_categories:
                selected.append(row)
                seen_categories.add(code)
            if len(selected) >= limit:
                break
        if len(selected) < min(limit, len(visible)):
            selected_ids = {row.id for row in selected}
            for row in visible:
                if row.id not in selected_ids:
                    selected.append(row)
                if len(selected) >= limit:
                    break
        return selected[:limit]

    def _route(self, row: Route) -> BotRoute:
        points = []
        for link in sorted(row.route_places, key=lambda item: item.position):
            place = link.place
            if place is None or not self._public_place(place) or not is_route_point_bot_eligible(place):
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
        return BotRoute(
            id=row.id,
            title=row.title,
            short_description=row.short_description,
            duration_minutes=row.duration_minutes,
            distance_km=row.distance_km,
            points=points,
            slug=row.slug,
        )

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
            slug=row.slug,
        )

    def _field_confidence(self, place_id: int, field_name: str) -> PlaceFieldConfidence | None:
        return self.db.query(PlaceFieldConfidence).filter_by(place_id=place_id, field_name=field_name).first()

    def _projected_route_rows(self, city: City, limit: int) -> list[Place]:
        location = (city.center_lat, city.center_lng) if city.center_lat is not None and city.center_lng is not None else None
        ctx = SimpleNamespace(city_id=city.slug, location=location, radius_meters=50_000,
                              avoided_place_ids=[], avoided_categories=[], destination_id=None)
        return routing_projection_candidates(self.db, ctx)[:limit]


def _points_distance_km(points: list[BotRoutePoint]) -> float:
    distance_m = 0.0
    for current, next_point in zip(points, points[1:]):
        if current.lat is None or current.lng is None or next_point.lat is None or next_point.lng is None:
            continue
        distance_m += haversine_meters(current.lat, current.lng, next_point.lat, next_point.lng)
    return distance_m / 1000


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


def _bot_place_from_public(row, *, distance_m: int | None = None) -> BotPlace:
    return BotPlace(id=row.id, title=row.title, category=row.category, category_name=row.category_label,
                    short_description=row.short_description, address=row.address, image_url=_safe_image_url(row.image_url),
                    opening_hours_display=_format_opening_hours(row.opening_hours), hours_reliable=False,
                    lat=row.lat, lng=row.lng, distance_m=distance_m, slug=row.slug)
