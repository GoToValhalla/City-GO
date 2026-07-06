"""Destination geo-search and geo-candidate → destination/scope conversion."""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass

from sqlalchemy.orm import Session

from models.destination import Destination, DestinationScope
from schemas.destination_geo import DestinationGeoCandidateInput, DestinationGeoCandidateRead
from services.destination_admin_validation import validate_bbox, validate_destination_type, validate_required_text, validate_slug
from services.place_address_geocode import geocoder_user_agent

NOMINATIM_SEARCH = "https://nominatim.openstreetmap.org/search"


@dataclass(frozen=True)
class DestinationGeoCandidate:
    candidate_key: str
    title: str
    display_name: str | None
    lat: float
    lng: float
    bbox: dict[str, float] | None
    osm_type: str | None
    osm_id: int | None
    destination_type: str
    import_strategy: str


def search_destination_geo_candidates(query: str, *, limit: int = 5) -> list[DestinationGeoCandidate]:
    cleaned = query.strip()
    if not cleaned:
        return []
    if _adapter_name() == "deterministic":
        return _deterministic_candidates(cleaned, limit=limit)
    return _nominatim_candidates(cleaned, limit=limit)


def candidate_from_input(data: DestinationGeoCandidateInput) -> DestinationGeoCandidate:
    bbox = validate_bbox(data.bbox)
    return DestinationGeoCandidate(
        candidate_key=data.candidate_key,
        title=data.title.strip(),
        display_name=data.display_name,
        lat=float(data.lat),
        lng=float(data.lng),
        bbox=bbox,
        osm_type=data.osm_type,
        osm_id=data.osm_id,
        destination_type=validate_destination_type(data.destination_type),
        import_strategy=data.import_strategy,
    )


def to_read_model(candidate: DestinationGeoCandidate) -> DestinationGeoCandidateRead:
    return DestinationGeoCandidateRead(
        candidate_key=candidate.candidate_key,
        title=candidate.title,
        display_name=candidate.display_name,
        lat=candidate.lat,
        lng=candidate.lng,
        bbox=candidate.bbox,
        osm_type=candidate.osm_type,
        osm_id=candidate.osm_id,
        destination_type=candidate.destination_type,
        import_strategy=candidate.import_strategy,
    )


def build_destination_payload(
    candidate: DestinationGeoCandidate,
    *,
    slug: str | None = None,
    name: str | None = None,
    destination_type: str | None = None,
) -> dict[str, object]:
    resolved_name = validate_required_text(name or candidate.title, "Название")
    resolved_slug = validate_slug(slug or resolved_name)
    resolved_type = validate_destination_type(destination_type or candidate.destination_type)
    bbox = candidate.bbox or _point_bbox(candidate.lat, candidate.lng)
    return {
        "slug": resolved_slug,
        "name": resolved_name,
        "destination_type": resolved_type,
        "center_lat": candidate.lat,
        "center_lng": candidate.lng,
        "bbox": bbox,
        "launch_status": "draft",
        "is_published": False,
        "is_active": True,
    }


def build_scope_payload(
    candidate: DestinationGeoCandidate,
    *,
    code: str | None = None,
    name: str | None = None,
    import_profile: str = "tourist_core",
    enabled: bool = True,
) -> dict[str, object]:
    resolved_name = validate_required_text(name or candidate.title, "Название контура")
    resolved_code = validate_slug(code or resolved_name)
    bbox = candidate.bbox or _point_bbox(candidate.lat, candidate.lng)
    return {
        "code": resolved_code,
        "name": resolved_name,
        "scope_type": "catalog",
        "import_strategy": candidate.import_strategy,
        "bbox": bbox,
        "import_profile": import_profile,
        "enabled": enabled,
        "priority": 0,
    }


def recover_or_create_scope(
    db: Session,
    destination: Destination,
    candidate: DestinationGeoCandidate,
    *,
    code: str | None = None,
    name: str | None = None,
    import_profile: str = "tourist_core",
    enabled: bool = True,
    recover: bool = True,
) -> tuple[DestinationScope, str]:
    data = build_scope_payload(candidate, code=code, name=name, import_profile=import_profile, enabled=enabled)
    existing = (
        db.query(DestinationScope)
        .filter_by(destination_id=destination.id, code=str(data["code"]))
        .first()
    )
    if existing is not None and recover:
        for key in ("name", "bbox", "import_strategy", "import_profile", "enabled"):
            setattr(existing, key, data[key])
        return existing, "recovered"
    if existing is not None:
        raise ValueError("Scope code already exists")
    scope = DestinationScope(destination_id=destination.id, **data)
    db.add(scope)
    db.flush()
    return scope, "created"


def _adapter_name() -> str:
    return os.getenv("CITYGO_DESTINATION_GEO_ADAPTER", "nominatim").strip().lower()


def _nominatim_candidates(query: str, *, limit: int) -> list[DestinationGeoCandidate]:
    params = urllib.parse.urlencode({"format": "jsonv2", "q": query, "limit": str(limit), "accept-language": "ru"})
    req = urllib.request.Request(f"{NOMINATIM_SEARCH}?{params}", headers={"User-Agent": geocoder_user_agent()})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return []
    if not isinstance(payload, list):
        return []
    return [_candidate_from_nominatim(row) for row in payload if isinstance(row, dict)]


def _deterministic_candidates(query: str, *, limit: int) -> list[DestinationGeoCandidate]:
    base = DestinationGeoCandidate(
        candidate_key=f"relation:9001",
        title="Куршская коса",
        display_name="Куршская коса, Калининградская область",
        lat=55.17,
        lng=20.86,
        bbox={"south": 54.94, "west": 20.43, "north": 55.32, "east": 20.99},
        osm_type="relation",
        osm_id=9001,
        destination_type="tourist_cluster",
        import_strategy="osm_relation",
    )
    alt = DestinationGeoCandidate(
        candidate_key=f"node:9002",
        title=f"Тест: {query}",
        display_name=f"Тестовый кандидат для {query}",
        lat=54.96,
        lng=20.48,
        bbox={"south": 54.9, "west": 20.4, "north": 55.0, "east": 20.6},
        osm_type="node",
        osm_id=9002,
        destination_type="city",
        import_strategy="single_bbox",
    )
    items = [base, alt]
    return items[: max(1, limit)]


def _candidate_from_nominatim(row: dict[str, object]) -> DestinationGeoCandidate:
    lat = float(row["lat"])
    lng = float(row["lon"])
    osm_type = str(row.get("osm_type") or "") or None
    osm_id_raw = row.get("osm_id")
    osm_id = int(osm_id_raw) if osm_id_raw is not None else None
    key = f"{osm_type}:{osm_id}" if osm_type and osm_id is not None else f"point:{lat:.5f}:{lng:.5f}"
    title = str(row.get("name") or row.get("display_name") or key)
    return DestinationGeoCandidate(
        candidate_key=key,
        title=title,
        display_name=str(row.get("display_name") or "") or None,
        lat=lat,
        lng=lng,
        bbox=_bbox_from_nominatim(row.get("boundingbox")),
        osm_type=osm_type,
        osm_id=osm_id,
        destination_type=_infer_destination_type(row),
        import_strategy="osm_relation" if osm_type == "relation" else "single_bbox",
    )


def _infer_destination_type(row: dict[str, object]) -> str:
    place_type = str(row.get("type") or "").lower()
    category = str(row.get("category") or row.get("class") or "").lower()
    if "national_park" in category or category == "protected_area":
        return "national_park"
    if place_type in {"city", "town", "village"}:
        return "city"
    if place_type == "administrative":
        return "region"
    if place_type in {"natural", "wood", "beach", "water"}:
        return "natural_region"
    return "tourist_cluster"


def _bbox_from_nominatim(value: object) -> dict[str, float] | None:
    if not isinstance(value, list) or len(value) < 4:
        return None
    try:
        south, north, west, east = float(value[0]), float(value[1]), float(value[2]), float(value[3])
    except (TypeError, ValueError):
        return None
    return validate_bbox({"south": south, "north": north, "west": west, "east": east})


def _point_bbox(lat: float, lng: float, delta: float = 0.05) -> dict[str, float]:
    return {"south": lat - delta, "north": lat + delta, "west": lng - delta, "east": lng + delta}
