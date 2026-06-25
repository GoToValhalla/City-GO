from __future__ import annotations

from functools import lru_cache
from typing import Any

import httpx

from core.config import settings
from schemas.walking_route import (
    WalkingRouteLeg,
    WalkingRoutePoint,
    WalkingRouteResponse,
    WalkingRouteStep,
)


_MODIFIER_LABELS = {
    "left": "налево",
    "slight left": "плавно налево",
    "sharp left": "резко налево",
    "right": "направо",
    "slight right": "плавно направо",
    "sharp right": "резко направо",
    "straight": "прямо",
    "uturn": "развернитесь",
}


def _instruction(step: dict[str, Any]) -> str:
    maneuver = step.get("maneuver") or {}
    kind = str(maneuver.get("type") or "continue")
    modifier = str(maneuver.get("modifier") or "").strip()
    street = str(step.get("name") or "").strip()
    street_suffix = f" на {street}" if street else ""

    if kind == "depart":
        return f"Начните движение{street_suffix}"
    if kind == "arrive":
        return "Точка назначения будет рядом"
    if kind in {"turn", "end of road"}:
        direction = _MODIFIER_LABELS.get(modifier, "в нужном направлении")
        return f"Поверните {direction}{street_suffix}"
    if kind in {"fork", "merge", "on ramp", "off ramp"}:
        direction = _MODIFIER_LABELS.get(modifier, "по нужному ответвлению")
        return f"Держитесь {direction}{street_suffix}"
    if kind in {"roundabout", "rotary", "roundabout turn"}:
        exit_number = maneuver.get("exit")
        exit_text = f", съезд {exit_number}" if exit_number else ""
        return f"На круговом движении продолжайте путь{exit_text}{street_suffix}"
    if kind == "new name":
        return f"Продолжайте движение{street_suffix}"
    direction = _MODIFIER_LABELS.get(modifier, "прямо")
    return f"Продолжайте {direction}{street_suffix}"


def _coordinates_key(points: list[WalkingRoutePoint]) -> tuple[tuple[float, float], ...]:
    return tuple((round(point.lat, 6), round(point.lng, 6)) for point in points)


def _parse_response(payload: dict[str, Any]) -> WalkingRouteResponse:
    routes = payload.get("routes") or []
    if payload.get("code") != "Ok" or not routes:
        raise ValueError(str(payload.get("message") or "pedestrian router returned no route"))
    route = routes[0]
    geometry = (route.get("geometry") or {}).get("coordinates") or []
    if len(geometry) < 2:
        raise ValueError("pedestrian router returned empty geometry")

    legs: list[WalkingRouteLeg] = []
    for index, leg in enumerate(route.get("legs") or []):
        steps = [
            WalkingRouteStep(
                instruction=_instruction(step),
                street_name=str(step.get("name") or "").strip() or None,
                distance_meters=float(step.get("distance") or 0),
                duration_seconds=float(step.get("duration") or 0),
            )
            for step in (leg.get("steps") or [])
            if float(step.get("distance") or 0) > 0 or (step.get("maneuver") or {}).get("type") == "arrive"
        ]
        legs.append(WalkingRouteLeg(
            from_index=index,
            to_index=index + 1,
            distance_meters=float(leg.get("distance") or 0),
            duration_seconds=float(leg.get("duration") or 0),
            steps=steps,
        ))

    return WalkingRouteResponse(
        status="routed",
        provider="osrm-foot",
        geometry=[(float(item[0]), float(item[1])) for item in geometry],
        distance_meters=float(route.get("distance") or 0),
        duration_seconds=float(route.get("duration") or 0),
        legs=legs,
    )


@lru_cache(maxsize=512)
def _cached_walking_route(coordinates: tuple[tuple[float, float], ...]) -> WalkingRouteResponse:
    base_url = settings.walking_router_url.rstrip("/")
    if not base_url:
        raise RuntimeError("walking router is not configured")
    coordinate_path = ";".join(f"{lng},{lat}" for lat, lng in coordinates)
    response = httpx.get(
        f"{base_url}/{coordinate_path}",
        params={"overview": "full", "geometries": "geojson", "steps": "true"},
        timeout=settings.walking_router_timeout_seconds,
        headers={"User-Agent": settings.walking_router_user_agent},
        follow_redirects=True,
    )
    response.raise_for_status()
    return _parse_response(response.json())


def build_walking_route(points: list[WalkingRoutePoint]) -> WalkingRouteResponse:
    try:
        return _cached_walking_route(_coordinates_key(points))
    except (httpx.HTTPError, RuntimeError, TypeError, ValueError):
        return WalkingRouteResponse(
            status="unavailable",
            provider="osrm-foot",
            geometry=[],
            warning=(
                "Не удалось получить пешеходный путь по улицам. "
                "Точки показаны без соединяющей линии, чтобы не вести через здания."
            ),
        )
