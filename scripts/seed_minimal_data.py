from datetime import datetime, time

from db.session import SessionLocal
from models.category import Category
from models.city import City
from models.city_candidate import CityCandidate
from models.collection import Collection
from models.collection_place import CollectionPlace
from models.country import Country
from models.place import Place
from models.region import Region
from models.place_schedule import PlaceSchedule
from models.place_tag import PlaceTag
from models.route import Route
from models.route_place import RoutePlace
from models.tag import Tag


# Минимальный seed-набор для локальной и тестовой среды.
# Здесь храним стартовые города, категории, места и маршруты.
SEED_DATA = {
    "cities": [
        {
            "slug": "zelenogradsk",
            "name": "Зеленоградск",
            "region": "Калининградская область",
            "country": "Россия",
            "timezone": "Europe/Kaliningrad",
            "center_lat": 54.9587,
            "center_lng": 20.4750,
        },
        {
            "slug": "kaliningrad",
            "name": "Калининград",
            "region": "Калининградская область",
            "country": "Россия",
            "timezone": "Europe/Kaliningrad",
            "center_lat": 54.7104,
            "center_lng": 20.4522,
        },
        {
            "slug": "khanty-mansiysk",
            "name": "Ханты-Мансийск",
            "region": "Ханты-Мансийский автономный округ",
            "country": "Россия",
            "timezone": "Asia/Yekaterinburg",
            "center_lat": 61.0042,
            "center_lng": 69.0039,
        },
        {
            "slug": "kutaisi",
            "name": "Кутаиси",
            "region": "Имеретия",
            "country": "Грузия",
            "timezone": "Asia/Tbilisi",
            "center_lat": 42.2679,
            "center_lng": 42.6940,
        },
        {
            "slug": "yerevan",
            "name": "Ереван",
            "region": "Ереван",
            "country": "Армения",
            "timezone": "Asia/Yerevan",
            "center_lat": 40.1872,
            "center_lng": 44.5152,
        },
        {
            "slug": "rostov-on-don",
            "name": "Ростов-на-Дону",
            "region": "Ростовская область",
            "country": "Россия",
            "timezone": "Europe/Moscow",
            "center_lat": 47.2357,
            "center_lng": 39.7015,
        },
    ],
    "categories": [
        {"code": "cafe", "name": "Кафе"},
        {"code": "walk", "name": "Прогулка"},
    ],
    "places": [
        {
            "city_slug": "zelenogradsk",
            "category_code": "cafe",
            "slug": "balt-zelenogradsk",
            "title": "Balt",
            "short_description": "Гастро-точка в центре Зеленоградска.",
            "image_url": "https://images.unsplash.com/photo-1554118811-1e0d58224f24?auto=format&fit=crop&w=1200&q=80",
            "category": "cafe",
            "address": "Зеленоградск, центр города",
            "lat": 54.9594,
            "lng": 20.4761,
            "price_level": 3,
            "dog_friendly": False,
            "family_friendly": True,
            "indoor": True,
            "outdoor": False,
        },
        {
            "city_slug": "zelenogradsk",
            "category_code": "walk",
            "slug": "promenade-zelenogradsk",
            "title": "Променад",
            "short_description": "Пешеходная прогулка вдоль моря.",
            "image_url": "https://images.unsplash.com/photo-1507525428034-b723cf961d3e?auto=format&fit=crop&w=1200&q=80",
            "category": "walk",
            "address": "Зеленоградск, променад",
            "lat": 54.9585,
            "lng": 20.4748,
            "price_level": 1,
            "dog_friendly": True,
            "family_friendly": True,
            "indoor": False,
            "outdoor": True,
        },
        {
            "city_slug": "kaliningrad",
            "category_code": "walk",
            "slug": "kant-island-kaliningrad",
            "title": "Остров Канта",
            "short_description": "Прогулочная и туристическая точка в центре Калининграда.",
            "image_url": "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=1200&q=80",
            "category": "walk",
            "address": "Калининград, остров Канта",
            "lat": 54.7066,
            "lng": 20.5124,
            "price_level": 1,
            "dog_friendly": True,
            "family_friendly": True,
            "indoor": False,
            "outdoor": True,
        },
    ],
    "routes": [
        {
            "city_slug": "zelenogradsk",
            "slug": "seaside-walk-zelenogradsk",
            "title": "Пешая прогулка по Зеленоградску",
            "short_description": "Короткий прогулочный маршрут по центру и променаду.",
            "duration_minutes": 60,
            "distance_km": 2.4,
            "route_mode": "walk",
            "points": [
                {"place_slug": "balt-zelenogradsk", "position": 1},
                {"place_slug": "promenade-zelenogradsk", "position": 2},
            ],
        },
        {
            "city_slug": "zelenogradsk",
            "slug": "seaside-public-transport-zelenogradsk",
            "title": "Маршрут по Зеленоградску на общественном транспорте",
            "short_description": "Черновой транспортный сценарий для теста режима public transport в текущем городе.",
            "duration_minutes": 35,
            "distance_km": 4.1,
            "route_mode": "public_transport",
            "points": [
                {"place_slug": "balt-zelenogradsk", "position": 1},
                {"place_slug": "promenade-zelenogradsk", "position": 2},
            ],
        },
        {
            "city_slug": "zelenogradsk",
            "slug": "mixed-seaside-zelenogradsk",
            "title": "Смешанный маршрут по Зеленоградску",
            "short_description": "Черновой mixed-сценарий: часть пути пешком, часть с транспортом.",
            "duration_minutes": 50,
            "distance_km": 3.6,
            "route_mode": "mixed",
            "points": [
                {"place_slug": "balt-zelenogradsk", "position": 1},
                {"place_slug": "promenade-zelenogradsk", "position": 2},
            ],
        },
        {
            "city_slug": "kaliningrad",
            "slug": "kant-walk-kaliningrad",
            "title": "Прогулка к острову Канта",
            "short_description": "Базовый туристический маршрут по центральной точке Калининграда.",
            "duration_minutes": 45,
            "distance_km": 1.8,
            "route_mode": "walk",
            "points": [
                {"place_slug": "kant-island-kaliningrad", "position": 1},
            ],
        },
        {
            "city_slug": "kaliningrad",
            "slug": "kant-public-transport-kaliningrad",
            "title": "Маршрут на общественном транспорте до острова Канта",
            "short_description": "Черновой сценарий для transport-mode маршрутов.",
            "duration_minutes": 30,
            "distance_km": 4.6,
            "route_mode": "public_transport",
            "points": [
                {"place_slug": "kant-island-kaliningrad", "position": 1},
            ],
        },
    ],
}


# Создает город, если его еще нет в базе; если существует — обеспечивает published статус.
def get_or_create_city(db, item: dict) -> City:
    city = db.query(City).filter(City.slug == item["slug"]).first()
    if city:
        if city.launch_status != "published" or not city.is_active:
            city.launch_status = "published"
            city.is_active = True
            city.updated_at = datetime.utcnow()
            db.flush()
        return city

    city = City(
        slug=item["slug"],
        name=item["name"],
        region=item.get("region"),
        country=item.get("country", "Россия"),
        timezone=item.get("timezone", "Europe/Kaliningrad"),
        center_lat=item.get("center_lat"),
        center_lng=item.get("center_lng"),
        launch_status="published",
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(city)
    db.flush()
    return city


# Создает категорию, если она еще не добавлена.
def get_or_create_category(db, item: dict) -> Category:
    category = db.query(Category).filter(Category.code == item["code"]).first()
    if category:
        return category

    category = Category(
        code=item["code"],
        name=item["name"],
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(category)
    db.flush()
    return category


# Создает место, если оно еще не существует.
def get_or_create_place(db, item: dict, city_id: int, category_id: int) -> Place:
    place = db.query(Place).filter(Place.slug == item["slug"]).first()
    if place:
        return place

    place = Place(
        city_id=city_id,
        category_id=category_id,
        slug=item["slug"],
        title=item["title"],
        short_description=item["short_description"],
        image_url=item.get("image_url"),
        category=item["category"],
        address=item["address"],
        lat=item["lat"],
        lng=item["lng"],
        price_level=item["price_level"],
        dog_friendly=item["dog_friendly"],
        family_friendly=item["family_friendly"],
        indoor=item["indoor"],
        outdoor=item["outdoor"],
        is_active=True,
        # Dev seed: явно публикуем места, чтобы не полагаться на дефолты модели.
        is_published=True,
        is_visible_in_catalog=True,
        is_route_eligible=True,
        is_searchable=True,
        publication_status="published",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(place)
    db.flush()
    return place


# Добавляет базовое расписание для места, если его еще нет.
def ensure_schedule(db, place_id: int) -> None:
    existing = db.query(PlaceSchedule).filter(PlaceSchedule.place_id == place_id).first()
    if existing:
        return

    for weekday in ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]:
        db.add(
            PlaceSchedule(
                place_id=place_id,
                weekday=weekday,
                open_time=time(9, 0),
                close_time=time(23, 0),
                is_closed=False,
                created_at=datetime.utcnow(),
            )
        )


# Создает маршрут, если его еще нет.
def get_or_create_route(db, item: dict, city_id: int) -> Route:
    route = db.query(Route).filter(Route.slug == item["slug"]).first()
    if route:
        return route

    route = Route(
        city_id=city_id,
        slug=item["slug"],
        title=item["title"],
        short_description=item.get("short_description"),
        duration_minutes=item.get("duration_minutes"),
        distance_km=item.get("distance_km"),
        route_mode=item.get("route_mode", "walk"),
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(route)
    db.flush()
    return route


# Добавляет точки маршрута, если они еще не созданы.
def ensure_route_points(db, route: Route, item: dict, place_map: dict[str, Place]) -> None:
    existing = db.query(RoutePlace).filter(RoutePlace.route_id == route.id).first()
    if existing:
        return

    for point in item["points"]:
        place = place_map[point["place_slug"]]
        db.add(
            RoutePlace(
                route_id=route.id,
                place_id=place.id,
                position=point["position"],
                created_at=datetime.utcnow(),
            )
        )


# Главная функция seed-скрипта.
# Создает города, категории, места, расписание и маршруты.
def main() -> None:
    db = SessionLocal()

    try:
        city_map: dict[str, City] = {}
        category_map: dict[str, Category] = {}
        place_map: dict[str, Place] = {}

        for city_item in SEED_DATA["cities"]:
            city = get_or_create_city(db, city_item)
            city_map[city.slug] = city

        for category_item in SEED_DATA["categories"]:
            category = get_or_create_category(db, category_item)
            category_map[category.code] = category

        for place_item in SEED_DATA["places"]:
            city = city_map[place_item["city_slug"]]
            category = category_map[place_item["category_code"]]

            place = get_or_create_place(
                db=db,
                item=place_item,
                city_id=city.id,
                category_id=category.id,
            )
            ensure_schedule(db, place.id)
            place_map[place.slug] = place

        for route_item in SEED_DATA["routes"]:
            city = city_map[route_item["city_slug"]]
            route = get_or_create_route(db, route_item, city.id)
            ensure_route_points(db, route, route_item, place_map)

        db.commit()
        print("Minimal multi-city seed with routes completed.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()