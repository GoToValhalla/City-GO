from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from math import atan2, cos, radians, sin, sqrt
from pathlib import Path
from typing import Any

import httpx

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from db.session import SessionLocal
from models.category import Category
from models.city import City
from models.place import Place

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
SOURCE = "osm_discovery"
OSM_URL = "https://www.openstreetmap.org/{kind}/{osm_id}"
POI_FILTERS = {
    "tourism": ["attraction", "museum", "gallery", "viewpoint"],
    "historic": ["castle", "monument", "memorial", "ruins", "archaeological_site", "monastery"],
    "amenity": ["theatre", "arts_centre", "cafe", "restaurant"],
    "leisure": ["park", "garden", "nature_reserve"],
    "natural": ["beach", "peak", "waterfall"],
}
CATEGORY_MAP = {
    "museum": "museum",
    "gallery": "museum",
    "viewpoint": "viewpoint",
    "castle": "historic",
    "monument": "historic",
    "memorial": "historic",
    "ruins": "historic",
    "archaeological_site": "historic",
    "monastery": "religious_site",
    "theatre": "culture",
    "arts_centre": "culture",
    "park": "park",
    "garden": "park",
    "nature_reserve": "nature",
    "beach": "nature",
    "peak": "nature",
    "waterfall": "nature",
    "cafe": "food",
    "restaurant": "food",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Discover missing OSM POI candidates and save them as draft places.")
    parser.add_argument("--city", dest="city_slug", default=None)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    db = SessionLocal()
    try:
        results = run_discovery(db, city_slug=args.city_slug, limit=args.limit, apply=args.apply)
        if args.apply:
            db.commit()
        else:
            db.rollback()
        output = {"apply": bool(args.apply), "cities": results, "total_created": sum(int(row["created"]) for row in results)}
        print(json.dumps(output, ensure_ascii=False, sort_keys=True), flush=True)
        print("POI_DISCOVERY_SUMMARY_JSON=" + json.dumps(output, ensure_ascii=False, sort_keys=True), flush=True)
    finally:
        db.close()


def run_discovery(db, *, city_slug: str | None, limit: int, apply: bool) -> list[dict[str, object]]:
    query = db.query(City).filter(City.is_active.is_(True), City.launch_status == "published")
    if city_slug:
        query = query.filter(City.slug == city_slug)
    cities = query.order_by(City.slug.asc()).all()
    category_ids = {str(code): int(category_id) for code, category_id in db.query(Category.code, Category.id).all()}
    return [discover_city(db, city, category_ids=category_ids, limit=limit, apply=apply) for city in cities]


def discover_city(db, city: City, *, category_ids: dict[str, int], limit: int, apply: bool) -> dict[str, object]:
    summary = {"city_slug": city.slug, "city_name": city.name, "fetched": 0, "created": 0, "duplicates": 0, "skipped": 0, "errors": [], "places": []}
    bbox = city_bbox(city)
    if bbox is None:
        summary["errors"].append("city_bbox_missing")
        return summary
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(OVERPASS_URL, data={"data": overpass_query(bbox, limit)})
            response.raise_for_status()
            elements = list((response.json() or {}).get("elements") or [])
    except Exception as exc:
        summary["errors"].append(f"overpass_error:{exc.__class__.__name__}")
        return summary

    summary["fetched"] = len(elements)
    existing_places = db.query(Place).filter(Place.city_id == city.id).all()
    existing_source_urls = {place.source_url for place in existing_places if place.source_url}
    existing_slugs = {place.slug for place in existing_places if place.slug}

    for element in elements:
        candidate = candidate_from_element(city, element)
        if candidate is None:
            summary["skipped"] += 1
            continue
        if is_duplicate(candidate, existing_places, existing_source_urls):
            summary["duplicates"] += 1
            continue
        if apply:
            place = build_place(candidate, category_ids, existing_slugs)
            db.add(place)
            db.flush()
            existing_places.append(place)
            existing_source_urls.add(place.source_url)
            existing_slugs.add(place.slug)
            summary["places"].append({"id": place.id, "title": place.title, "category": place.canonical_category})
        else:
            summary["places"].append({"title": candidate["title"], "category": candidate["category"], "source_url": candidate["source_url"]})
        summary["created"] += 1
    summary["places"] = summary["places"][:20]
    return summary


def city_bbox(city: City) -> tuple[float, float, float, float] | None:
    bbox = city.bbox or {}
    south = first_number(bbox, "min_lat", "south", "s")
    north = first_number(bbox, "max_lat", "north", "n")
    west = first_number(bbox, "min_lng", "west", "w")
    east = first_number(bbox, "max_lng", "east", "e")
    if None in (south, west, north, east):
        return None
    return float(south), float(west), float(north), float(east)


def first_number(payload: dict[str, object], *keys: str) -> float | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                pass
    return None


def overpass_query(bbox: tuple[float, float, float, float], limit: int) -> str:
    south, west, north, east = bbox
    clauses = []
    for key, values in POI_FILTERS.items():
        pattern = "|".join(re.escape(value) for value in values)
        clauses.append(f'nwr["{key}"~"^({pattern})$"]({south},{west},{north},{east});')
    return "[out:json][timeout:25];\n(\n  " + "\n  ".join(clauses) + f"\n);\nout center tags {max(1, int(limit))};"


def candidate_from_element(city: City, element: dict[str, Any]) -> dict[str, Any] | None:
    tags = element.get("tags") or {}
    title = best_name(tags)
    lat = element.get("lat") or (element.get("center") or {}).get("lat")
    lng = element.get("lon") or (element.get("center") or {}).get("lon")
    if not title or lat is None or lng is None:
        return None
    osm_type = str(element.get("type") or "node")
    osm_id = int(element.get("id"))
    return {
        "city_id": city.id,
        "title": title,
        "lat": float(lat),
        "lng": float(lng),
        "category": category_from_tags(tags),
        "source_url": OSM_URL.format(kind=osm_type, osm_id=osm_id),
        "tags": tags,
    }


def best_name(tags: dict[str, Any]) -> str | None:
    for key in ("name:ru", "name", "name:en", "official_name", "alt_name"):
        value = tags.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def category_from_tags(tags: dict[str, Any]) -> str:
    for key in ("tourism", "historic", "amenity", "leisure", "natural"):
        value = tags.get(key)
        if isinstance(value, str) and value in CATEGORY_MAP:
            return CATEGORY_MAP[value]
    return "attraction"


def is_duplicate(candidate: dict[str, Any], places: list[Place], source_urls: set[str]) -> bool:
    if candidate["source_url"] in source_urls:
        return True
    title = normalize_title(candidate["title"])
    for place in places:
        if normalize_title(place.title) == title and distance_meters(candidate["lat"], candidate["lng"], place.lat, place.lng) <= 75:
            return True
    return False


def build_place(candidate: dict[str, Any], category_ids: dict[str, int], existing_slugs: set[str]) -> Place:
    tags = candidate["tags"]
    address = address_from_tags(tags)
    slug = unique_slug(slugify(candidate["title"]), existing_slugs)
    now = datetime.utcnow()
    return Place(
        city_id=candidate["city_id"],
        category_id=category_ids.get(candidate["category"]),
        slug=slug,
        title=candidate["title"],
        address=address,
        address_source="osm" if address else None,
        address_confidence=0.6 if address else None,
        source=SOURCE,
        source_url=candidate["source_url"],
        website=tag_value(tags, "website"),
        phone=tag_value(tags, "phone"),
        confidence=0.55,
        status="active",
        canonical_category=candidate["category"],
        lifecycle_status="active",
        quality_tier="bronze",
        quality_score=35,
        completeness_score=10,
        photo_score=0,
        description_score=0,
        confidence_score=4,
        freshness_score=3,
        existence_confidence_score=45,
        existence_confidence_level="medium",
        verification_status="unverified",
        verification_source="osm",
        verification_method="discovery",
        verification_comment="draft candidate from OSM discovery",
        lat=candidate["lat"],
        lng=candidate["lng"],
        category=candidate["category"],
        opening_hours=opening_hours_from_tags(tags),
        is_active=True,
        is_published=False,
        is_visible_in_catalog=False,
        is_route_eligible=False,
        is_searchable=False,
        publication_status="draft",
        created_at=now,
        updated_at=now,
    )


def address_from_tags(tags: dict[str, Any]) -> str | None:
    parts = [tag_value(tags, key) for key in ("addr:street", "addr:housenumber", "addr:city")]
    clean = [part for part in parts if part]
    return ", ".join(clean) if clean else None


def opening_hours_from_tags(tags: dict[str, Any]) -> dict[str, object] | None:
    value = tag_value(tags, "opening_hours")
    return {"raw": value, "source": "osm"} if value else None


def tag_value(tags: dict[str, Any], key: str) -> str | None:
    value = tags.get(key)
    return value.strip() if isinstance(value, str) and value.strip() else None


def slugify(value: str) -> str:
    return re.sub(r"[^\w]+", "-", value.lower(), flags=re.UNICODE).strip("-")[:80] or "poi"


def unique_slug(base: str, existing_slugs: set[str]) -> str:
    candidate = base
    index = 2
    while candidate in existing_slugs:
        candidate = f"{base}-{index}"
        index += 1
    return candidate


def normalize_title(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().casefold())


def distance_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    earth_radius = 6371000.0
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return earth_radius * 2 * atan2(sqrt(a), sqrt(1 - a))


if __name__ == "__main__":
    main()
