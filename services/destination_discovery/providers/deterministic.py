"""Deterministic discovery provider for tests and offline dev."""

from __future__ import annotations

from schemas.destination_discovery import DiscoveryWarning, GeoBbox, GeoPoint, RegionCandidate

_KGD = RegionCandidate(
    id="test:RU-KGD",
    provider="deterministic",
    name="Калининградская область",
    local_name="Калининградская область",
    english_name="Kaliningrad Oblast",
    country="Russia",
    admin_level=4,
    type="region",
    center=GeoPoint(lat=54.75, lon=20.45),
    bbox=GeoBbox(south=54.25, west=19.60, north=55.35, east=22.90),
    importance_score=0.95,
    matched_query="",
    warnings=[],
)

_REGIONS: dict[str, RegionCandidate] = {
    "test:RU-KGD": _KGD,
    "test:RU-KDA": RegionCandidate(
        id="test:RU-KDA",
        provider="deterministic",
        name="Краснодарский край",
        local_name="Краснодарский край",
        english_name="Krasnodar Krai",
        country="Russia",
        admin_level=4,
        type="region",
        center=GeoPoint(lat=45.04, lon=38.98),
        bbox=GeoBbox(south=43.0, west=36.5, north=46.5, east=41.5),
        importance_score=0.92,
        matched_query="",
        warnings=[DiscoveryWarning(code="LARGE_REGION", severity="warning", message="Крупный регион — проверьте предложения вручную.")],
    ),
    "test:AM": RegionCandidate(
        id="test:AM",
        provider="deterministic",
        name="Армения",
        local_name="Հայաստան",
        english_name="Armenia",
        country="Armenia",
        admin_level=2,
        type="country",
        center=GeoPoint(lat=40.18, lon=44.51),
        bbox=GeoBbox(south=38.84, west=43.45, north=41.30, east=46.63),
        importance_score=0.88,
        matched_query="",
        warnings=[DiscoveryWarning(code="LARGE_REGION", severity="warning", message="Страна целиком — предложения могут быть неполными.")],
    ),
    "test:GE": RegionCandidate(
        id="test:GE",
        provider="deterministic",
        name="Грузия",
        local_name="საქართველო",
        english_name="Georgia",
        country="Georgia",
        admin_level=2,
        type="country",
        center=GeoPoint(lat=41.72, lon=44.79),
        bbox=GeoBbox(south=41.05, west=40.01, north=43.59, east=46.74),
        importance_score=0.88,
        matched_query="",
        warnings=[DiscoveryWarning(code="LARGE_REGION", severity="warning", message="Страна целиком — предложения могут быть неполными.")],
    ),
}

_SEARCH_ALIASES: dict[str, str] = {
    "калининградская": "test:RU-KGD",
    "калининградская область": "test:RU-KGD",
    "kaliningrad oblast": "test:RU-KGD",
    "краснодарский": "test:RU-KDA",
    "краснодарский край": "test:RU-KDA",
    "krasnodar krai": "test:RU-KDA",
    "армения": "test:AM",
    "armenia": "test:AM",
    "грузия": "test:GE",
    "georgia": "test:GE",
}


def search_regions(query: str, *, limit: int = 5) -> list[RegionCandidate]:
    key = query.strip().lower()
    if not key:
        return []
    region_id = _SEARCH_ALIASES.get(key)
    if region_id is None:
        for alias, rid in _SEARCH_ALIASES.items():
            if key in alias or alias in key:
                region_id = rid
                break
    if region_id is None:
        return []
    region = _REGIONS[region_id]
    return [region.model_copy(update={"matched_query": query.strip()})]


def get_region(region_id: str) -> RegionCandidate | None:
    return _REGIONS.get(region_id)


def raw_candidates_for_region(region_id: str) -> list[dict[str, object]]:
    if region_id != "test:RU-KGD":
        return []
    return [
        {"external_id": "kaliningrad", "name": "Калининград", "english_name": "Kaliningrad", "type": "city", "population": 489359, "lat": 54.7104, "lon": 20.5109, "bbox": {"south": 54.62, "west": 20.36, "north": 54.78, "east": 20.62}, "importance": 0.98},
        {"external_id": "zelenogradsk", "name": "Зеленоградск", "english_name": "Zelenogradsk", "type": "town", "population": 16434, "lat": 54.9594, "lon": 20.4767, "bbox": {"south": 54.90, "west": 20.40, "north": 55.00, "east": 20.55}, "importance": 0.86},
        {"external_id": "svetlogorsk", "name": "Светлогорск", "english_name": "Svetlogorsk", "type": "town", "population": 10772, "lat": 54.9431, "lon": 20.1515, "bbox": {"south": 54.90, "west": 20.10, "north": 54.98, "east": 20.22}, "importance": 0.84},
        {"external_id": "baltiysk", "name": "Балтийск", "english_name": "Baltiysk", "type": "town", "population": 26796, "lat": 54.6510, "lon": 19.9142, "bbox": {"south": 54.60, "west": 19.80, "north": 54.70, "east": 20.05}, "importance": 0.72, "border": True},
        {"external_id": "yantarny", "name": "Янтарный", "english_name": "Yantarny", "type": "town", "population": 4779, "lat": 54.8716, "lon": 19.9433, "bbox": {"south": 54.84, "west": 19.88, "north": 54.90, "east": 20.00}, "importance": 0.70},
        {"external_id": "chernyakhovsk", "name": "Черняховск", "english_name": "Chernyakhovsk", "type": "town", "population": 36170, "lat": 54.6334, "lon": 21.8156, "bbox": {"south": 54.55, "west": 21.70, "north": 54.70, "east": 21.95}, "importance": 0.68, "poi_unknown": True},
    ]
