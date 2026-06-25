from __future__ import annotations

from functools import lru_cache
from typing import Any

import httpx

from core.config import settings
from schemas.walking_route import WalkingRouteLeg, WalkingRoutePoint, WalkingRouteResponse, WalkingRouteStep

_MODIFIER_LABELS = {
    "left": "налево", "slight left": "плавно налево", "sharp left": "резко налево",
    "right": "направо", "slight right": "плавно направо", "sharp right": "резко направо",
    "straight": "прямо", "uturn": "развернитесь",
}


def _instruction(step: dict[str, Any]) -> str:
    maneuver = step.get("maneuver") or {}
    kind = str(maneuver.get("type") or "continue")
    modifier = str(maneuver.get("modifier") or "").strip()
    street = str(step.get("name") or "").strip()
    street_suffix = f" на {street}" if street else ""
    if kind == "depart": return f"Начните движение{street_suffix}"
    if kind == "arrive": return "Точка назначения будет рядом"
    if kind in {"turn", "end of road"}:
        return f"Поверните {_MODIFIER_LABELS.get(modifier, 'в нужном направлении')}{street_suffix}"
    if kind in {"fork", "merge", "on ramp", "off ramp"}:
        return f"Держитесь {_MODIFIER_LABELS.get(modifier, 'по нужному ответвлению')}{street_suffix}"
    if kind in {"roundabout", "rotary", "roundabout turn"}:
        exit_number = maneuver.get("exit")
        return f"На круговом движении продолжайте путь{f', съезд {exit_number}' if exit_number else ''}{street_suffix}"
    if kind == "new name": return f"Продолжайте движение{street_suffix}"
    return f"Продолжайте {_MODIFIER_LABELS.get(modifier, 'прямо')}{street_suffix}"


def _coordinates_key(points: list[WalkingRoutePoint]) -> tuple[tuple[float, float], ...]:
    return tuple((round(point.lat, 6), round(point.lng, 6)) for point in points)


def _parse_osrm(payload: dict[str, Any]) -> WalkingRouteResponse:
    routes = payload.get("routes") or []
    if payload.get("code") != "Ok" or not routes:
        raise ValueError(str(payload.get("message") or "pedestrian router returned no route"))
    route = routes[0]
    geometry = (route.get("geometry") or {}).get("coordinates") or []
    if len(geometry) < 2: raise ValueError("pedestrian router returned empty geometry")
    legs = []
    for index, leg in enumerate(route.get("legs") or []):
        steps = [WalkingRouteStep(
            instruction=_instruction(step), street_name=str(step.get("name") or "").strip() or None,
            distance_meters=float(step.get("distance") or 0), duration_seconds=float(step.get("duration") or 0),
        ) for step in (leg.get("steps") or []) if float(step.get("distance") or 0) > 0 or (step.get("maneuver") or {}).get("type") == "arrive"]
        legs.append(WalkingRouteLeg(
            from_index=index, to_index=index + 1, distance_meters=float(leg.get("distance") or 0),
            duration_seconds=float(leg.get("duration") or 0), steps=steps,
        ))
    return WalkingRouteResponse(
        status="routed", provider="osrm-foot",
        geometry=[(float(item[0]), float(item[1])) for item in geometry],
        distance_meters=float(route.get("distance") or 0), duration_seconds=float(route.get("duration") or 0), legs=legs,
    )


def _flatten_geometry(value: Any) -> list[tuple[float, float]]:
    result: list[tuple[float, float]] = []
    def visit(node: Any) -> None:
        if isinstance(node, list) and len(node) >= 2 and all(isinstance(item, (int, float)) for item in node[:2]):
            point = (float(node[0]), float(node[1]))
            if not result or result[-1] != point: result.append(point)
            return
        if isinstance(node, list):
            for child in node: visit(child)
    visit(value)
    return result


def _parse_geoapify(payload: dict[str, Any]) -> WalkingRouteResponse:
    features = payload.get("features") or []
    if not features: raise ValueError("Geoapify returned no walking route")
    feature = features[0]
    properties = feature.get("properties") or {}
    geometry = _flatten_geometry((feature.get("geometry") or {}).get("coordinates") or [])
    if len(geometry) < 2: raise ValueError("Geoapify returned empty geometry")
    legs = []
    for index, leg in enumerate(properties.get("legs") or []):
        steps = []
        for step in leg.get("steps") or []:
            instruction = step.get("instruction") or {}
            text = instruction.get("text") if isinstance(instruction, dict) else instruction
            steps.append(WalkingRouteStep(
                instruction=str(text or "Продолжайте движение"), street_name=str(step.get("name") or "").strip() or None,
                distance_meters=float(step.get("distance") or 0), duration_seconds=float(step.get("time") or 0),
            ))
        legs.append(WalkingRouteLeg(
            from_index=index, to_index=index + 1, distance_meters=float(leg.get("distance") or 0),
            duration_seconds=float(leg.get("time") or 0), steps=steps,
        ))
    return WalkingRouteResponse(
        status="routed", provider="geoapify-walk", geometry=geometry,
        distance_meters=float(properties.get("distance") or 0), duration_seconds=float(properties.get("time") or 0), legs=legs,
    )


def _fetch_geoapify(coordinates: tuple[tuple[float, float], ...]) -> WalkingRouteResponse:
    response = httpx.get(
        "https://api.geoapify.com/v1/routing",
        params={
            "waypoints": "|".join(f"{lat},{lng}" for lat, lng in coordinates),
            "mode": "walk", "details": "instruction_details", "lang": "ru", "apiKey": settings.geoapify_api_key,
        },
        timeout=settings.walking_router_timeout_seconds,
        headers={"User-Agent": settings.walking_router_user_agent},
    )
    response.raise_for_status()
    return _parse_geoapify(response.json())


def _fetch_osrm(coordinates: tuple[tuple[float, float], ...]) -> WalkingRouteResponse:
    base_url = settings.walking_router_url.rstrip("/")
    if not base_url: raise RuntimeError("walking router is not configured")
    coordinate_path = ";".join(f"{lng},{lat}" for lat, lng in coordinates)
    response = httpx.get(
        f"{base_url}/{coordinate_path}", params={"overview": "full", "geometries": "geojson", "steps": "true"},
        timeout=settings.walking_router_timeout_seconds, headers={"User-Agent": settings.walking_router_user_agent}, follow_redirects=True,
    )
    response.raise_for_status()
    return _parse_osrm(response.json())


@lru_cache(maxsize=512)
def _cached_walking_route(coordinates: tuple[tuple[float, float], ...]) -> WalkingRouteResponse:
    if settings.geoapify_api_key:
        try: return _fetch_geoapify(coordinates)
        except (httpx.HTTPError, TypeError, ValueError): pass
    return _fetch_osrm(coordinates)


def build_walking_route(points: list[WalkingRoutePoint]) -> WalkingRouteResponse:
    try:
        return _cached_walking_route(_coordinates_key(points))
    except (httpx.HTTPError, RuntimeError, TypeError, ValueError):
        return WalkingRouteResponse(
            status="unavailable", provider="none", geometry=[],
            warning="Не удалось получить пешеходный путь по улицам. Точки показаны без соединяющей линии, чтобы не вести через здания.",
        )
