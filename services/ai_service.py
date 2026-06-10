"""
Разбор текстового AI-запроса: эвристики по словарям + вызовы read-only сервисов для ответа.
"""

from sqlalchemy.orm import Session

from services.ai_dictionaries import (
    CATEGORY_KEYWORDS,
    CITY_KEYWORDS,
    INTENT_KEYWORDS,
    TAG_KEYWORDS,
)
from services.collection_service import get_collections_by_city_id
from services.nearby_service import get_nearby_places
from services.open_now_service import get_open_now_places
from services.place_detail_service import get_place_detail_by_slug
from services.place_service import get_places
from services.route_service import get_routes_by_city_id


def detect_city_slug(query: str) -> str | None:
    normalized_query = query.lower()

    for city_slug, keywords in CITY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in normalized_query:
                return city_slug

    return None


def detect_city_id(city_slug: str | None) -> int | None:
    if city_slug == "zelenogradsk":
        return 1

    return None


def detect_category_id(query: str) -> int | None:
    normalized_query = query.lower()

    for category_id, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in normalized_query:
                return category_id

    return None


def detect_tag_id(query: str) -> int | None:
    normalized_query = query.lower()

    for tag_id, keywords in TAG_KEYWORDS.items():
        for keyword in keywords:
            if keyword in normalized_query:
                return tag_id

    return None


def detect_place_slug(query: str) -> str | None:
    normalized_query = query.lower()

    if "place-5" in normalized_query:
        return "place-5"

    return None


def detect_intent(query: str) -> str:
    normalized_query = query.lower()

    for intent, keywords in INTENT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in normalized_query:
                return intent

    return "unknown"


def filter_places_for_ai(places: list) -> list:
    filtered = []

    for place in places:
        title = (place.title or "").lower()
        slug = (place.slug or "").lower()

        if "seed" in slug:
            continue
        if "point" in slug:
            continue
        if "точка" in title:
            continue
        if "зона" in title:
            continue
        if "кластер" in title:
            continue

        filtered.append(place)

    return filtered


def rank_places_for_ai(places: list, query: str) -> list:
    normalized_query = query.lower()

    wants_quiet = any(
        word in normalized_query
        for word in ["тихо", "тихие", "тихий", "спокойно", "спокойные"]
    )
    wants_romantic = any(word in normalized_query for word in ["романт", "свидан"])
    wants_dog = any(
        word in normalized_query for word in ["с собак", "dog-friendly", "dog friendly"]
    )

    def score(place) -> tuple:
        title = (place.title or "").lower()
        category = (place.category or "").lower()
        address = (place.address or "").lower()
        slug = (place.slug or "").lower()

        relevance_bonus = 0

        if wants_quiet:
            if category == "museum":
                relevance_bonus -= 4
            if "музей" in title:
                relevance_bonus -= 3
            if "quiet" in slug or "тих" in title or "спокой" in title or "спокой" in address:
                relevance_bonus -= 4
            if "кафе" in title or "кофейня" in title:
                relevance_bonus -= 1
            if "семейн" in title:
                relevance_bonus += 2
            if "информационно-туристический" in title:
                relevance_bonus += 4
            if "променад" in title:
                relevance_bonus += 2

        if wants_romantic:
            if category == "cafe":
                relevance_bonus -= 3
            if "у моря" in address:
                relevance_bonus -= 2
            if category == "walk":
                relevance_bonus -= 1

        if wants_dog:
            if place.dog_friendly:
                relevance_bonus -= 4
            else:
                relevance_bonus += 3

        return (
            relevance_bonus,
            place.price_level if place.price_level is not None else 99,
            place.id,
        )

    return sorted(places, key=score)


def process_ai_query(
    query: str,
    db: Session,
    lat: float | None = None,
    lng: float | None = None,
) -> dict:
    city_slug = detect_city_slug(query)
    city_id = detect_city_id(city_slug)
    category_id = detect_category_id(query)
    tag_id = detect_tag_id(query)
    place_slug = detect_place_slug(query)
    intent = detect_intent(query)

    if place_slug is not None:
        place = get_place_detail_by_slug(db=db, slug=place_slug)

        return {
            "status": "accepted",
            "intent": "place_detail",
            "city_slug": city_slug,
            "place_slug": place_slug,
            "query": query,
            "message": "Определен сценарий place_detail. Возвращены детали места.",
            "results": place,
        }

    if category_id is not None or tag_id is not None:
        places = get_places(
            db=db,
            city_id=city_id,
            city_slug=city_slug,
            category_id=category_id,
            tag_id=tag_id,
        )

        filtered_places = filter_places_for_ai(places)
        ranked_places = rank_places_for_ai(filtered_places, query)[:10]

        results = [
            {
                "id": place.id,
                "slug": place.slug,
                "title": place.title,
                "city_id": place.city_id,
                "category_id": place.category_id,
                "category": place.category,
                "address": place.address,
            }
            for place in ranked_places
        ]

        return {
            "status": "accepted",
            "intent": "places_filtered",
            "city_slug": city_slug,
            "category_id": category_id,
            "tag_id": tag_id,
            "query": query,
            "message": "Определен сценарий places_filtered. Возвращены лучшие места по категории и/или тегу.",
            "results": results,
        }

    if intent == "collections":
        collections = get_collections_by_city_id(db=db, city_id=city_id or 1)

        results = [
            {
                "id": collection.id,
                "slug": collection.slug,
                "title": collection.title,
                "city_id": collection.city_id,
                "short_description": collection.short_description,
                "is_active": collection.is_active,
            }
            for collection in collections
        ]

        return {
            "status": "accepted",
            "intent": "collections",
            "city_slug": city_slug,
            "query": query,
            "message": "Определен сценарий collections. Возвращены подборки по городу.",
            "results": results,
        }

    if intent == "routes":
        routes = get_routes_by_city_id(db=db, city_id=city_id or 1)

        results = [
            {
                "id": route.id,
                "slug": route.slug,
                "title": route.title,
                "city_id": route.city_id,
                "short_description": route.short_description,
                "duration_minutes": route.duration_minutes,
                "is_active": route.is_active,
            }
            for route in routes
        ]

        return {
            "status": "accepted",
            "intent": "routes",
            "city_slug": city_slug,
            "query": query,
            "message": "Определен сценарий routes. Возвращены маршруты по городу.",
            "results": results,
        }

    if intent == "open_now":
        open_now_places = get_open_now_places(
            db=db,
            city_slug=city_slug or "zelenogradsk",
        )

        return {
            "status": "accepted",
            "intent": "open_now",
            "city_slug": city_slug,
            "query": query,
            "message": "Определен сценарий open_now. Возвращены места, открытые сейчас.",
            "results": open_now_places,
        }

    if intent == "nearby":
        nearby_places = get_nearby_places(
            db=db,
            lat=lat or 54.9586,
            lng=lng or 20.4751,
            radius_km=3.0,
        )

        return {
            "status": "accepted",
            "intent": "nearby",
            "city_slug": city_slug,
            "query": query,
            "message": "Определен сценарий nearby. Возвращены ближайшие места.",
            "results": nearby_places,
        }

    return {
        "status": "accepted",
        "intent": "unknown",
        "city_slug": city_slug,
        "query": query,
        "message": "Интент пока не распознан. Нужна дальнейшая логика разбора запроса.",
        "results": [],
    }
