"""BBox helpers for v1 membership (no PostGIS on hot path)."""

from __future__ import annotations


def point_in_bbox(lat: float, lng: float, bbox: dict[str, object] | None) -> bool:
    if not bbox:
        return False
    try:
        south = float(bbox.get("south") or bbox.get("min_lat") or bbox.get("lat_min"))
        north = float(bbox.get("north") or bbox.get("max_lat") or bbox.get("lat_max"))
        west = float(bbox.get("west") or bbox.get("min_lng") or bbox.get("lng_min"))
        east = float(bbox.get("east") or bbox.get("max_lng") or bbox.get("lng_max"))
    except (TypeError, ValueError):
        return False
    return south <= lat <= north and west <= lng <= east


def city_bbox_from_model(city) -> dict[str, float] | None:
    raw = getattr(city, "bbox", None)
    if isinstance(raw, dict) and raw:
        return raw
    lat = getattr(city, "center_lat", None)
    lng = getattr(city, "center_lng", None)
    if lat is None or lng is None:
        return None
    pad = 0.05
    return {"south": lat - pad, "north": lat + pad, "west": lng - pad, "east": lng + pad}
