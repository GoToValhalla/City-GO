"""LEGACY ITINERARY TEXT PARSER.

Status: part of the old `/routes/generate` itinerary stack.

Active route intent/source-of-truth:
- `services.route_builder_flow`
- user route request contracts and route draft/session flows.

Rules:
- Do not add new route intent parsing behavior here.
- Keep only for old itinerary endpoint compatibility until consumers migrate.
"""

import re
from typing import Any

from schemas.itinerary import ItineraryGenerateRequest


# Ключевые слова для anti-tourist сценария.
ANTI_TOURIST_KEYWORDS = [
    "без толп",
    "без туристов",
    "не туристический",
    "не туристическое",
    "непопсовое",
    "не попсовое",
    "локальное",
    "локальный",
    "тихое",
    "тихий",
    "спокойное",
    "спокойный",
]


# Ключевые слова для интересов пользователя.
INTEREST_KEYWORDS_MAP = {
    "coffee": ["кофе", "кофейня", "кофейни", "coffee"],
    "food": ["еда", "поесть", "перекусить", "обед", "ужин", "ресторан", "кафе"],
    "sea": ["море", "морю", "у моря", "побережье", "набережная", "променад"],
    "architecture": ["архитектура", "здания", "домики", "исторические здания"],
    "museum": ["музей", "музеи", "выставка", "галерея"],
    "walk": ["погулять", "прогулка", "маршрут", "пройтись", "гулять"],
    "quiet": ["тихо", "спокойно", "спокойный", "тихий", "без суеты"],
    "romantic": ["романтично", "романтический", "на вечер", "вдвоем"],
}


# Ключевые слова для режима передвижения.
# Порядок распознавания потом контролируем отдельно,
# чтобы более специфичные режимы не перебивались walk.
ROUTE_MODE_KEYWORDS_MAP = {
    "walk": [
        "пешком",
        "пеший",
        "пешая прогулка",
        "пеший маршрут",
        "гулять",
        "пройтись",
    ],
    "public_transport": [
        "общественный транспорт",
        "на автобусе",
        "на транспорте",
        "автобус",
        "метро",
        "трамвай",
        "электричка",
    ],
    "car": [
        "на машине",
        "машиной",
        "на авто",
        "на автомобиле",
        "автомобилем",
        "за рулем",
    ],
    "bike": [
        "на велосипеде",
        "велосипедом",
        "вело",
        "веломаршрут",
        "bike",
        "bike route",
    ],
    "mixed": [
        "смешанный",
        "комбинированный",
        "часть пешком",
        "частично пешком",
    ],
}


# Ключевые слова для темпа маршрута.
PACE_KEYWORDS_MAP = {
    "slow": ["не спеша", "спокойно", "медленно", "без беготни", "расслабленно"],
    "normal": ["обычно", "нормально", "средний темп"],
    "fast": ["быстро", "интенсивно", "побыстрее", "активно"],
}


# Извлекает явное ограничение по времени из свободного текста.
# Поддерживаем простые варианты:
# - "70 минут"
# - "2 часа"
# - "1.5 часа"
def extract_time_budget_minutes(query: str) -> int | None:
    normalized_query = query.lower().strip()

    minutes_match = re.search(r"(\d+)\s*мин", normalized_query)
    if minutes_match:
        return int(minutes_match.group(1))

    hours_match = re.search(r"(\d+(?:[.,]\d+)?)\s*час", normalized_query)
    if hours_match:
        hours_raw = hours_match.group(1).replace(",", ".")
        hours_value = float(hours_raw)
        return int(hours_value * 60)

    return None


# Определяет time_mode:
# - explicit_budget, если в тексте есть явное время
# - open_duration, если нет.
def extract_time_mode(query: str) -> str:
    time_budget_minutes = extract_time_budget_minutes(query)

    if time_budget_minutes is not None:
        return "explicit_budget"

    return "open_duration"


# Определяет режим передвижения по тексту.
# Сначала проверяем более специфичные режимы, потом walk.
def extract_route_mode(query: str) -> str | None:
    normalized_query = query.lower().strip()

    mode_priority = [
        "public_transport",
        "car",
        "bike",
        "mixed",
        "walk",
    ]

    for route_mode in mode_priority:
        keywords = ROUTE_MODE_KEYWORDS_MAP.get(route_mode, [])

        for keyword in keywords:
            if keyword in normalized_query:
                return route_mode

    return None


# Извлекает сценарные интересы из текста пользователя.
def extract_route_preferences(query: str) -> dict[str, Any]:
    normalized_query = query.lower().strip()

    preferences: dict[str, Any] = {
        "interests": [],
        "anti_tourist": False,
        "pace_mode": None,
    }

    # Ищем anti-tourist сигналы.
    for keyword in ANTI_TOURIST_KEYWORDS:
        if keyword in normalized_query:
            preferences["anti_tourist"] = True
            break

    # Ищем интересы пользователя.
    for interest_code, keywords in INTEREST_KEYWORDS_MAP.items():
        for keyword in keywords:
            if keyword in normalized_query:
                preferences["interests"].append(interest_code)
                break

    # Ищем темп маршрута.
    for pace_mode, keywords in PACE_KEYWORDS_MAP.items():
        for keyword in keywords:
            if keyword in normalized_query:
                preferences["pace_mode"] = pace_mode
                break

        if preferences["pace_mode"] is not None:
            break

    return preferences


# Извлекает базовые ограничения из текста пользователя.
def extract_route_constraints(query: str) -> dict[str, Any]:
    normalized_query = query.lower().strip()

    constraints: dict[str, Any] = {
        "with_dog": False,
        "with_children": False,
        "indoor_only": False,
        "outdoor_only": False,
    }

    # Маршрут с собакой.
    if "с собакой" in normalized_query or "dog friendly" in normalized_query:
        constraints["with_dog"] = True

    # Маршрут с детьми.
    if "с ребенком" in normalized_query or "с детьми" in normalized_query:
        constraints["with_children"] = True

    # Indoor / outdoor ограничения.
    if "только внутри" in normalized_query or "только indoor" in normalized_query:
        constraints["indoor_only"] = True

    if "только на улице" in normalized_query or "только outdoor" in normalized_query:
        constraints["outdoor_only"] = True

    return constraints


# Разбирает свободный текст пользователя в один нормализованный словарь.
def parse_route_intent(query: str | None) -> dict[str, Any]:
    if not query:
        return {
            "query": None,
            "time_mode": "open_duration",
            "time_budget_minutes": None,
            "route_mode": None,
            "preferences": {
                "interests": [],
                "anti_tourist": False,
                "pace_mode": None,
            },
            "constraints": {
                "with_dog": False,
                "with_children": False,
                "indoor_only": False,
                "outdoor_only": False,
            },
        }

    return {
        "query": query,
        "time_mode": extract_time_mode(query),
        "time_budget_minutes": extract_time_budget_minutes(query),
        "route_mode": extract_route_mode(query),
        "preferences": extract_route_preferences(query),
        "constraints": extract_route_constraints(query),
    }


# Объединяет явные поля запроса и то, что распарсили из текста.
# Явные поля всегда приоритетнее текстовых догадок.
def merge_explicit_fields_and_text_constraints(
    request: ItineraryGenerateRequest,
    parsed_intent: dict[str, Any],
) -> dict[str, Any]:
    parsed_preferences = parsed_intent.get("preferences", {})
    parsed_constraints = parsed_intent.get("constraints", {})

    explicit_interests: list[str] = []

    if request.with_dog:
        parsed_constraints["with_dog"] = True

    if request.with_children:
        parsed_constraints["with_children"] = True

    if request.indoor_only:
        parsed_constraints["indoor_only"] = True

    if request.outdoor_only:
        parsed_constraints["outdoor_only"] = True

    if parsed_constraints.get("with_dog"):
        explicit_interests.append("dog_friendly")

    merged_context = {
        "time_mode": request.time_mode or parsed_intent.get("time_mode", "open_duration"),
        "time_budget_minutes": (
            request.time_budget_minutes
            if request.time_budget_minutes is not None
            else parsed_intent.get("time_budget_minutes")
        ),
        "route_mode": request.route_mode or parsed_intent.get("route_mode") or "walk",
        "preferences": {
            "interests": [*parsed_preferences.get("interests", []), *explicit_interests],
            "anti_tourist": parsed_preferences.get("anti_tourist", False),
            "pace_mode": parsed_preferences.get("pace_mode"),
        },
        "with_dog": parsed_constraints.get("with_dog", False),
        "with_children": parsed_constraints.get("with_children", False),
        "indoor_only": parsed_constraints.get("indoor_only", False),
        "outdoor_only": parsed_constraints.get("outdoor_only", False),
        "budget_level": request.budget_level,
        "return_to_start": request.return_to_start,
        "trip_days": request.trip_days,
    }

    return merged_context
