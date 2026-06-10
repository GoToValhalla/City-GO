"""
Определение стартовой геоточки маршрута из place_id, геолокации устройства или якоря города.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


class StartSource(str, Enum):
    PLACE_ID = "place_id"
    GEO_DEVICE = "geo_device"
    CITY_ANCHOR = "city_anchor"
    LEGACY_GEO = "legacy_geo"
    INVALID = "invalid"


class AccuracyTier(str, Enum):
    PRECISE = "precise"
    APPROXIMATE = "approximate"
    ANCHOR = "anchor"


GEO_PRECISE_MAX_M: int = 150
GEO_APPROXIMATE_MAX_M: int = 800


@dataclass
class ResolvedStartContext:
    lat: float
    lng: float
    source: StartSource
    accuracy_tier: AccuracyTier
    display_label: str
    raw_address: Optional[str] = field(default=None)
    warning_message: Optional[str] = field(default=None)


def resolve_from_place_id(
    place_id: int,
    db: "Session",
) -> Optional[ResolvedStartContext]:
    from models.place import Place

    place = db.get(Place, place_id)
    if place is None:
        return None

    if place.lat is None or place.lng is None:
        return None

    return ResolvedStartContext(
        lat=float(place.lat),
        lng=float(place.lng),
        source=StartSource.PLACE_ID,
        accuracy_tier=AccuracyTier.PRECISE,
        display_label=place.title,
    )


def resolve_from_geo(
    lat: float,
    lng: float,
    accuracy_m: Optional[int],
) -> Optional[ResolvedStartContext]:
    if accuracy_m is None:
        return ResolvedStartContext(
            lat=float(lat),
            lng=float(lng),
            source=StartSource.GEO_DEVICE,
            accuracy_tier=AccuracyTier.APPROXIMATE,
            display_label="Your location",
            warning_message="GPS accuracy unknown — time estimates may vary.",
        )

    if accuracy_m <= GEO_PRECISE_MAX_M:
        return ResolvedStartContext(
            lat=float(lat),
            lng=float(lng),
            source=StartSource.GEO_DEVICE,
            accuracy_tier=AccuracyTier.PRECISE,
            display_label="Your location",
        )

    if accuracy_m <= GEO_APPROXIMATE_MAX_M:
        return ResolvedStartContext(
            lat=float(lat),
            lng=float(lng),
            source=StartSource.GEO_DEVICE,
            accuracy_tier=AccuracyTier.APPROXIMATE,
            display_label="Your approximate location",
            warning_message=(
                f"GPS accuracy is ~{accuracy_m} m — distances and timing are estimates."
            ),
        )

    return None


def normalize_legacy_geo(
    lat: Optional[float],
    lng: Optional[float],
) -> Optional[ResolvedStartContext]:
    if lat is None or lng is None:
        return None

    return ResolvedStartContext(
        lat=float(lat),
        lng=float(lng),
        source=StartSource.LEGACY_GEO,
        accuracy_tier=AccuracyTier.APPROXIMATE,
        display_label="Your location",
        warning_message="Legacy coordinates used — accuracy unknown.",
    )


def resolve_city_anchor(
    db: "Session",
    city_slug: Optional[str] = None,
    city_name: Optional[str] = None,
) -> Optional[ResolvedStartContext]:
    from models.city import City

    city = None

    if city_slug:
        city = (
            db.query(City)
            .filter(City.slug == city_slug.strip().lower())
            .first()
        )

    if city is None and city_name:
        city = (
            db.query(City)
            .filter(City.name.ilike(city_name.strip()))
            .first()
        )

    if city is None:
        return None

    if city.center_lat is None or city.center_lng is None:
        return None

    return ResolvedStartContext(
        lat=float(city.center_lat),
        lng=float(city.center_lng),
        source=StartSource.CITY_ANCHOR,
        accuracy_tier=AccuracyTier.ANCHOR,
        display_label=f"City center · {city.name}",
        warning_message=(
            "Route starts from the city center. Share your location for a more accurate route."
        ),
    )


def resolve_start_context(
    *,
    place_id: Optional[int] = None,
    geo_lat: Optional[float] = None,
    geo_lng: Optional[float] = None,
    geo_acc_m: Optional[int] = None,
    address: Optional[str] = None,
    city_slug: Optional[str] = None,
    city_name: Optional[str] = None,
    legacy_lat: Optional[float] = None,
    legacy_lng: Optional[float] = None,
    db: Optional["Session"] = None,
) -> ResolvedStartContext:
    result: Optional[ResolvedStartContext] = None

    if place_id is not None and db is not None:
        result = resolve_from_place_id(place_id, db)

    if result is None and geo_lat is not None and geo_lng is not None:
        result = resolve_from_geo(geo_lat, geo_lng, geo_acc_m)

    if result is None and legacy_lat is not None and legacy_lng is not None:
        result = normalize_legacy_geo(legacy_lat, legacy_lng)

    if result is None and db is not None and (city_slug or city_name):
        result = resolve_city_anchor(
            db=db,
            city_slug=city_slug,
            city_name=city_name,
        )

    if result is None:
        return ResolvedStartContext(
            lat=0.0,
            lng=0.0,
            source=StartSource.INVALID,
            accuracy_tier=AccuracyTier.ANCHOR,
            display_label="Unknown start",
            raw_address=address,
            warning_message=(
                "Could not determine a start point. Provide geo coordinates, a place_id, or a city."
            ),
        )

    result.raw_address = address
    return result
