from __future__ import annotations

from dataclasses import dataclass
from math import asin, cos, radians, sin, sqrt
from typing import Iterable

from models.known_missing_poi import KnownMissingPoi


@dataclass(frozen=True)
class CoverageScopeSuggestion:
    city_slug: str
    suggested_type: str
    center_lat: float
    center_lng: float
    radius_meters: int
    reason: str
    gap_ids: list[int]
    expected_scope: str | None = None


def suggest_scopes_for_gaps(rows: Iterable[KnownMissingPoi]) -> list[CoverageScopeSuggestion]:
    """Create actionable scope suggestions from unresolved coverage gaps.

    MVP intentionally uses deterministic distance buckets instead of heavy clustering.
    This is enough to turn outside_bbox / not_imported_scope into admin actions for all cities.
    """

    suggestions: list[CoverageScopeSuggestion] = []
    by_city: dict[str, list[KnownMissingPoi]] = {}
    for row in rows:
        if row.status == "matched":
            continue
        if row.gap_reason not in {"outside_bbox", "not_imported_scope", "unsupported_tag", "source_absent"}:
            continue
        city_slug = row.city.slug if row.city else "unknown"
        by_city.setdefault(city_slug, []).append(row)

    for city_slug, city_rows in by_city.items():
        suggestions.extend(_suggest_for_city(city_slug, city_rows))
    return suggestions


def _suggest_for_city(city_slug: str, rows: list[KnownMissingPoi]) -> list[CoverageScopeSuggestion]:
    result: list[CoverageScopeSuggestion] = []
    clusters = _simple_clusters(rows, max_distance_m=2_000)
    for cluster in clusters:
        center_lat = sum(row.lat for row in cluster) / len(cluster)
        center_lng = sum(row.lng for row in cluster) / len(cluster)
        max_distance = max((_distance_m(center_lat, center_lng, row.lat, row.lng) for row in cluster), default=0.0)
        expected_scopes = {str(row.expected_scope or "") for row in cluster}
        expected_categories = {str(row.expected_category or "") for row in cluster}
        if len(cluster) == 1 and _is_critical(cluster[0]):
            suggested_type = "must_have_anchor"
            radius = 600
            reason = "isolated_critical_poi"
        elif expected_categories & {"monastery", "church", "cathedral", "culture", "heritage"} or any("heritage" in value for value in expected_scopes):
            suggested_type = "heritage_day_trip"
            radius = max(1_200, int(max_distance + 800))
            reason = "heritage_cluster"
        elif expected_categories & {"nature", "walk", "viewpoint", "beach"} or any("nature" in value for value in expected_scopes):
            suggested_type = "nature_area"
            radius = max(1_500, int(max_distance + 1_000))
            reason = "nature_cluster"
        else:
            suggested_type = "day_trip" if len(cluster) <= 3 else "city_district"
            radius = max(1_000, int(max_distance + 700))
            reason = "coverage_gap_cluster"
        result.append(
            CoverageScopeSuggestion(
                city_slug=city_slug,
                suggested_type=suggested_type,
                center_lat=round(center_lat, 6),
                center_lng=round(center_lng, 6),
                radius_meters=radius,
                reason=reason,
                gap_ids=[row.id for row in cluster],
                expected_scope=next(iter(expected_scopes - {""}), None),
            )
        )
    return result


def _simple_clusters(rows: list[KnownMissingPoi], *, max_distance_m: int) -> list[list[KnownMissingPoi]]:
    clusters: list[list[KnownMissingPoi]] = []
    for row in rows:
        for cluster in clusters:
            lat = sum(item.lat for item in cluster) / len(cluster)
            lng = sum(item.lng for item in cluster) / len(cluster)
            if _distance_m(lat, lng, row.lat, row.lng) <= max_distance_m:
                cluster.append(row)
                break
        else:
            clusters.append([row])
    return clusters


def _is_critical(row: KnownMissingPoi) -> bool:
    return str(row.expected_route_policy or "").lower() in {"critical", "must_have", "route_anchor"}


def _distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    earth_radius_m = 6_371_008.8
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    rlat1 = radians(lat1)
    rlat2 = radians(lat2)
    a = sin(dlat / 2) ** 2 + cos(rlat1) * cos(rlat2) * sin(dlng / 2) ** 2
    return 2 * earth_radius_m * asin(sqrt(a))
