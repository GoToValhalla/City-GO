import json
import re
from pathlib import Path


# Маппинг OSM-тегов в наши внутренние категории.
OSM_TO_CATEGORY = {
    "cafe": "cafe",
    "restaurant": "restaurant",
    "bar": "bar",
    "pub": "bar",
    "fast_food": "cafe",
    "ice_cream": "cafe",
    "bakery": "cafe",
    "museum": "museum",
    "library": "museum",
    "theatre": "entertainment",
    "cinema": "entertainment",
    "marketplace": "market",
    "place_of_worship": "church",
    "attraction": "landmark",
    "viewpoint": "viewpoint",
    "artwork": "landmark",
    "gallery": "gallery",
    "park": "park",
    "garden": "park",
    "beach": "walk",
    "promenade": "walk",
    "playground": "park",
    "sports_centre": "sport",
}


# Эвристика price_level по типу места.
PRICE_LEVEL_HINTS = {
    "fast_food": 1,
    "cafe": 2,
    "restaurant": 2,
    "bar": 2,
    "pub": 2,
}


# Дефолтная длительность посещения по категории.
DURATION_DEFAULTS = {
    "cafe": 30,
    "restaurant": 50,
    "bar": 35,
    "museum": 75,
    "gallery": 45,
    "park": 30,
    "walk": 25,
    "viewpoint": 15,
    "market": 30,
    "landmark": 15,
    "church": 20,
    "entertainment": 60,
    "sport": 60,
}


# Генерирует slug-based id для места.
def slugify(name: str) -> str:
    name = name.lower().strip()
    name = re.sub(r"[^a-zа-я0-9\s]", "", name)
    name = re.sub(r"\s+", "_", name)

    translit = {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ж": "zh", "з": "z",
        "и": "i", "й": "y", "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p",
        "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "h", "ц": "ts", "ч": "ch",
        "ш": "sh", "щ": "sch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    }

    name = "".join(translit.get(c, c) for c in name)
    name = re.sub(r"[^a-z0-9_]", "", name)

    return f"zrsk_{name[:40]}"


# Преобразует один OSM-элемент в наш place-объект.
# Если элемент бесполезен для продукта — возвращает None.
def transform_element(el: dict) -> dict | None:
    tags = el.get("tags", {})
    name = tags.get("name")

    # Без имени место нам не нужно.
    if not name:
        return None

    # Для node берем lat/lon напрямую, для way — center.
    lat = el.get("lat") or el.get("center", {}).get("lat")
    lng = el.get("lon") or el.get("center", {}).get("lon")

    # Если координат нет — пропускаем.
    if not lat or not lng:
        return None

    # Выбираем главный OSM-тип объекта.
    osm_type = (
        tags.get("amenity")
        or tags.get("tourism")
        or tags.get("leisure")
        or tags.get("shop")
    )

    # Преобразуем OSM-тип в нашу категорию.
    category = OSM_TO_CATEGORY.get(osm_type)
    if not category:
        return None

    return {
        "id": slugify(name),
        "city_id": "zelenogradsk",
        "name": name,
        "category": category,
        "lat": float(lat),
        "lng": float(lng),
        "price_level": PRICE_LEVEL_HINTS.get(osm_type, 0),
        "average_visit_duration_minutes": DURATION_DEFAULTS.get(category, 20),
        "opening_hours": tags.get("opening_hours"),
        "tags": [osm_type] if osm_type else [],
        "description": "",
        "active": True,
        # Ревью нужно, если нет opening_hours или price_level не определен.
        "_needs_review": (
            tags.get("opening_hours") is None
            or PRICE_LEVEL_HINTS.get(osm_type, 0) == 0
        ),
    }


# Читает raw OSM, трансформирует и сохраняет финальный seed-файл.
def main():
    raw_path = Path("data/raw/zelenogradsk_osm.json")
    output_path = Path("data/seeds/places/zelenogradsk.json")

    raw = json.loads(raw_path.read_text(encoding="utf-8"))

    places = []
    seen_ids = set()

    # Обрабатываем все элементы и убираем дубли по id.
    for el in raw.get("elements", []):
        place = transform_element(el)
        if not place:
            continue

        if place["id"] in seen_ids:
            continue

        seen_ids.add(place["id"])
        places.append(place)

    # Сортируем по имени для стабильного diff в git.
    places.sort(key=lambda p: p["name"])

    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        json.dumps(places, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Saved: {output_path}")
    print(f"Places: {len(places)}")


if __name__ == "__main__":
    main()