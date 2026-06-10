import json
import re
from datetime import datetime, timezone
from functools import reduce
from pathlib import Path
from typing import Any

DAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
BBOX = (54.92, 54.98, 20.44, 20.53)
RAW_PATH = Path("data/raw/zelenogradsk_osm.json")
OUT_PATH = Path("data/seeds/place_import/zelenogradsk_osm.json")
TYPE_TO_CATEGORY = {
    "cafe": "coffee", "fast_food": "coffee", "ice_cream": "coffee", "bakery": "coffee",
    "restaurant": "food", "bar": "bar", "pub": "bar", "museum": "museum",
    "library": "museum", "gallery": "museum", "theatre": "museum", "cinema": "bar",
    "attraction": "attraction", "viewpoint": "attraction", "artwork": "attraction",
    "monument": "attraction", "memorial": "attraction", "tower": "attraction",
    "park": "park", "garden": "park", "playground": "park", "picnic_site": "park",
    "fitness_station": "park", "beach": "walk", "pedestrian": "walk", "footway": "walk",
    "promenade": "walk", "pier": "walk", "hotel": "hotel", "marketplace": "service",
}
DURATION = {
    "coffee": 30, "food": 60, "bar": 120, "museum": 75, "attraction": 30,
    "park": 60, "walk": 45, "hotel": 30, "service": 30,
}
DEFAULT_HOURS = {"coffee": ("08:00", "21:00"), "food": ("11:00", "22:00"),
                 "bar": ("17:00", "01:00"), "museum": ("10:00", "18:00"),
                 "attraction": ("10:00", "19:00"), "park": ("00:00", "23:59"),
                 "walk": ("00:00", "23:59"), "hotel": ("00:00", "23:59"),
                 "service": ("10:00", "19:00")}
TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
}
def build_seed(raw: dict[str, Any], today: datetime | None = None) -> dict[str, object]:
    current = today or datetime.now(timezone.utc)
    places = tuple(filter(None, map(lambda el: place_from_element(el, current), raw.get("elements", []))))
    return {"items": deduplicate(places), "dry_run": True}
def place_from_element(el: dict[str, Any], today: datetime) -> dict[str, object] | None:
    tags = el.get("tags") or {}
    name = tags.get("name")
    lat, lng = el.get("lat") or el.get("center", {}).get("lat"), el.get("lon") or el.get("center", {}).get("lon")
    osm_type = (tags.get("amenity") or tags.get("leisure") or tags.get("tourism")
                or tags.get("shop") or tags.get("natural") or tags.get("historic")
                or tags.get("man_made") or tags.get("highway"))
    category = TYPE_TO_CATEGORY.get(str(osm_type))
    if not name or lat is None or lng is None or category is None or not in_bbox(float(lat), float(lng)):
        return None
    taxonomy = taxonomy_for(category, str(osm_type))
    return {
        "title": name,
        "slug": slug_for(str(name), category),
        "city_slug": "zelenogradsk",
        "category": category,
        "address": tags.get("addr:street"),
        "short_description": "",
        "taxonomy": taxonomy,
        "source": "osm",
        "source_url": f"https://www.openstreetmap.org/{el.get('type')}/{el.get('id')}",
        "confidence": 0.7 if tags.get("opening_hours") else 0.6,
        "last_verified_at": today.date().isoformat(),
        "status": "active",
        "lat": float(lat),
        "lng": float(lng),
        "opening_hours": opening_hours(str(tags.get("opening_hours") or ""), category),
        "average_visit_duration_minutes": DURATION[category],
        "price_level": price_level(str(osm_type)),
    }
def taxonomy_for(category: str, osm_type: str) -> dict[str, list[str] | str]:
    tag_map = {"coffee": ["indoor"], "food": ["indoor"], "bar": ["indoor", "open_late"],
               "museum": ["indoor", "historical"], "attraction": ["outdoor", "photo_spot"],
               "park": ["outdoor", "kid_friendly"], "walk": ["outdoor", "photo_spot"]}
    scenario_map = {"coffee": ["coffee_now"], "food": ["food_now"], "bar": ["evening_plan"],
                    "park": ["walk_now", "with_kids"], "walk": ["walk_now"]}
    vibes = ["cozy"] if osm_type in ("cafe", "bakery") else []
    return {"category": category, "tags": tag_map.get(category, []),
            "scenario_tags": scenario_map.get(category, []), "vibe_tags": vibes, "restriction_tags": []}
def opening_hours(raw: str, category: str) -> dict[str, dict[str, str]]:
    match = re.fullmatch(r"\s*(\d{1,2}:\d{2})-(\d{1,2}:\d{2})\s*", raw)
    source = match.groups() if match else DEFAULT_HOURS[category]
    return dict(map(lambda day: (day, {"open": source[0], "close": source[1]}), DAYS))
def slug_for(name: str, category: str) -> str:
    translit = "".join(TRANSLIT.get(char, char) for char in name.casefold())
    compact = re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", translit)).strip("-")
    return f"zelenogradsk-{category}-{compact[:48]}"
def in_bbox(lat: float, lng: float) -> bool:
    return BBOX[0] <= lat <= BBOX[1] and BBOX[2] <= lng <= BBOX[3]
def price_level(osm_type: str) -> int:
    return {"fast_food": 1, "cafe": 2, "restaurant": 2, "bar": 2, "pub": 2}.get(osm_type, 0)
def deduplicate(places: tuple[dict[str, object], ...]) -> list[dict[str, object]]:
    return reduce(lambda acc, place: acc if place["slug"] in {p["slug"] for p in acc} else [*acc, place], places, [])
def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(build_seed(json.loads(RAW_PATH.read_text())), ensure_ascii=False, indent=2))
    print(f"Saved {OUT_PATH}")
if __name__ == "__main__":
    main()
