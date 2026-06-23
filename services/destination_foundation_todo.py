"""TODO scaffold for City GO Destination Foundation V2.

This module is intentionally not imported by runtime code. It records the target classes and
migration points for moving from city-only data foundation to destination/region/area foundation.

Do not add these classes to SQLAlchemy Base metadata until migrations and backward-compatible
API contracts are designed.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class DestinationType(str, Enum):
    """TODO: target destination types for Data Foundation V2."""

    CITY = "city"
    NATURAL_REGION = "natural_region"
    NATIONAL_PARK = "national_park"
    TOURIST_CLUSTER = "tourist_cluster"
    ROUTE_CORRIDOR = "route_corridor"
    DISTRICT = "district"


class DestinationImportStrategy(str, Enum):
    """TODO: target import strategies replacing the city-center bbox-only approach."""

    SINGLE_BBOX = "single_bbox"
    OSM_RELATION = "osm_relation"
    MANUAL_POLYGON = "manual_polygon"
    TILED = "tiled"
    ROUTE_CORRIDOR = "route_corridor"
    PER_CHILD = "per_child"


class DestinationRouteType(str, Enum):
    """TODO: target route modes for destination-aware route planning."""

    CITY_WALK = "city_walk"
    AREA_WALK = "area_walk"
    REGION_DRIVE = "region_drive"
    MULTI_DAY = "multi_day"
    ROUTE_CORRIDOR = "route_corridor"
    CLUSTER_TOUR = "cluster_tour"


@dataclass(frozen=True)
class DestinationTodo:
    """TODO: future persistent Destination model.

    Target persistent fields:
    - slug, name, type, parent_id, country_id, region_id;
    - center_lat, center_lng, bbox, boundary, osm_relation_id;
    - launch_status, is_active, is_published, is_searchable;
    - readiness_score, quality_status, tourist_tier, expected_places_count.

    Migration rule:
    - every current City must get Destination(type='city');
    - keep City and city_id during the backward-compatible phase;
    - never model Baikal/Altai/Karelia as fake City rows.
    """

    slug: str
    destination_type: DestinationType


@dataclass(frozen=True)
class PlaceDestinationTodo:
    """TODO: future materialized Place <-> Destination relation.

    Target fields:
    - place_id;
    - destination_id;
    - is_primary;
    - assignment_type: legacy_city/spatial/manual/imported/route_corridor;
    - confidence;
    - source.

    Purpose:
    - avoid heavy ST_Within checks for each catalog/route request;
    - allow one Place to belong to Baikal, Olkhon and Irkutsk region at the same time;
    - keep publication/search/routing context-dependent.
    """

    place_id: int
    destination_slug: str
    is_primary: bool = False


@dataclass(frozen=True)
class DestinationImportScopeTodo:
    """TODO: future import scope owned by Destination, not only City.

    Target behavior:
    - city destinations may still use current single bbox import;
    - natural regions must use osm_relation/manual_polygon/tiled import;
    - route corridors must use buffered-line import;
    - tourist clusters may use per-child import;
    - utility categories must not pollute tourist catalog/route candidates.
    """

    destination_slug: str
    strategy: DestinationImportStrategy
    import_profile: str


@dataclass(frozen=True)
class DestinationPublicationTodo:
    """TODO: staged publication model for large regions.

    Target behavior:
    - publish destination with Tier 1 places first;
    - add Tier 2/3 gradually through review;
    - do not block the whole Baikal/Altai destination until every imported POI is reviewed;
    - place visibility may differ by destination context.
    """

    destination_slug: str
    publication_stage: str


@dataclass(frozen=True)
class DestinationRouteContextTodo:
    """TODO: future route context replacing city-only route candidate retrieval.

    Target behavior:
    - keep city_walk backward compatible;
    - add destination_slug/destination_type/route_type;
    - retrieve candidates by PlaceDestination membership, polygon/corridor, or child destinations;
    - fallback should expand spatial scope, not only city-wide scope.
    """

    destination_slug: str
    route_type: DestinationRouteType
