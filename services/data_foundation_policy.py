"""Source-of-truth constants for Data Foundation P0.

Здесь нет title-based правил. Категории, route eligibility и spam policy должны
опираться на канонические коды и source tags, а не на слова в названии места.
"""

from __future__ import annotations

# Runtime route generation must not require only perfect data.
# Gold/Silver are preferred by scoring, but Bronze is still route-eligible so cities with
# incomplete enrichment can build a real route instead of failing with an empty candidate pool.
ROUTE_ALLOWED_QUALITY_TIERS: frozenset[str] = frozenset({"gold", "silver", "bronze"})

CANONICAL_CATEGORIES: tuple[str, ...] = (
    "museum",
    "park",
    "viewpoint",
    "architecture",
    "beach",
    "embankment",
    "nature",
    "restaurant",
    "cafe",
    "bar",
    "theatre",
    "gallery",
    "shopping",
    "hotel",
    "landmark",
    "entertainment",
    "historical_site",
    "family",
    "sport",
    "attraction",
)

# Туристический продукт не должен тащить инфраструктурные POI в маршруты.
SPAM_POI_CATEGORIES: frozenset[str] = frozenset({
    "pharmacy",
    "atm",
    "fuel",
    "parking",
    "bus_stop",
    "public_toilet",
    "vending_machine",
    "bench",
    "waste_basket",
    "charging_station",
    "post_box",
    "hospital",
    "clinic",
    "police",
    "industrial",
    "office",
    "generic_service",
    "transport_stop",
    "tram_stop",
    "stop",
    "shelter",
    "toilet",
    "gas_station",
})

# Базовый seed для таблицы canonical_categories.
CANONICAL_CATEGORY_SEED: tuple[dict[str, object], ...] = tuple(
    {
        "code": code,
        "name_ru": {
            "museum": "Музей",
            "park": "Парк",
            "viewpoint": "Смотровая площадка",
            "architecture": "Архитектура",
            "beach": "Пляж",
            "embankment": "Набережная",
            "nature": "Природа",
            "restaurant": "Ресторан",
            "cafe": "Кафе",
            "bar": "Бар",
            "theatre": "Театр",
            "gallery": "Галерея",
            "shopping": "Шопинг",
            "hotel": "Гостиница",
            "landmark": "Достопримечательность",
            "entertainment": "Развлечения",
            "historical_site": "Историческое место",
            "family": "Для семьи",
            "sport": "Спорт",
            "attraction": "Аттракцион",
        }.get(code, code),
        "is_route_eligible": code not in {"hotel", "shopping"},
        "is_catalog_visible": True,
        "is_default_enabled": True,
        "is_spam_category": False,
    }
    for code in CANONICAL_CATEGORIES
)

# Явные OSM block rules для P0. Позже они переедут в управляемую таблицу spam_poi_rules.
OSM_SPAM_RULE_SEED: tuple[dict[str, str], ...] = (
    {"osm_key": "amenity", "osm_value": "pharmacy", "reason": "Аптека не является туристической точкой маршрута"},
    {"osm_key": "amenity", "osm_value": "atm", "reason": "Банкомат является инфраструктурой"},
    {"osm_key": "amenity", "osm_value": "fuel", "reason": "АЗС является инфраструктурой"},
    {"osm_key": "amenity", "osm_value": "parking", "reason": "Парковка является инфраструктурой"},
    {"osm_key": "highway", "osm_value": "bus_stop", "reason": "Остановка является транспортным слоем"},
    {"osm_key": "amenity", "osm_value": "toilets", "reason": "Туалет является инфраструктурой"},
    {"osm_key": "amenity", "osm_value": "vending_machine", "reason": "Вендинг является инфраструктурой"},
    {"osm_key": "amenity", "osm_value": "bench", "reason": "Скамейка не является туристической точкой"},
    {"osm_key": "amenity", "osm_value": "waste_basket", "reason": "Урна не является туристической точкой"},
    {"osm_key": "amenity", "osm_value": "charging_station", "reason": "Зарядная станция является инфраструктурой"},
    {"osm_key": "amenity", "osm_value": "post_box", "reason": "Почтовый ящик является инфраструктурой"},
)
