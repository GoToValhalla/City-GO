from __future__ import annotations

from typing import Protocol

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from models.product_event import ProductEvent
from schemas.external_navigation import (
    ExternalNavigationBlock,
    ExternalNavigationEventRequest,
    ExternalNavigationFullRoute,
    ExternalNavigationLink,
    ExternalNavigationPointLinks,
    ExternalNavigationSegment,
)
from services.product_event_service import record_event
from services.route_geometry import distance_meters, walk_minutes_between

_MAX_FULL_ROUTE_POINTS = 8
_MAX_FULL_ROUTE_URL_LENGTH = 1900
_MIN_SEGMENT_DISTANCE_M = 50


class NavigationWaypoint(Protocol):
    position: int
    lat: float | None
    lng: float | None


class ExternalNavigationService:
    """Provider-agnostic bridge from City GO routes to external map links."""

    def build_for_points(self, points: list[object]) -> ExternalNavigationBlock:
        total = len(points)
        valid = [_to_waypoint(point) for point in points if _has_valid_coords(point)]
        warnings: list[str] = []
        if total == 0:
            warnings.append("route_has_no_points")
        if len(valid) < total:
            warnings.append("some_points_have_no_valid_coordinates")
        if len(valid) < 2:
            warnings.append("not_enough_points_for_segment_navigation")

        return ExternalNavigationBlock(
            navigation_ready_pct=_pct(len(valid), total),
            destination_links=[self._destination_links(point) for point in valid],
            segments=self._segments(valid),
            full_route=self._full_route(valid),
            warnings=warnings,
        )

    def _destination_links(self, point: dict[str, object]) -> ExternalNavigationPointLinks:
        lat = float(point["lat"])
        lng = float(point["lng"])
        return ExternalNavigationPointLinks(
            point_index=int(point["index"]),
            place_id=_text(point.get("place_id")),
            title=_text(point.get("title")),
            lat=lat,
            lng=lng,
            links=[
                ExternalNavigationLink(
                    provider="yandex_maps",
                    mode="destination",
                    label="Открыть точку в Яндекс Картах",
                    web_url=_yandex_destination_url(lat, lng),
                    is_primary=True,
                ),
                ExternalNavigationLink(
                    provider="2gis",
                    mode="destination",
                    label="Открыть точку в 2ГИС",
                    web_url=_two_gis_destination_web_url(lat, lng),
                ),
            ],
        )

    def _segments(self, points: list[dict[str, object]]) -> list[ExternalNavigationSegment]:
        segments: list[ExternalNavigationSegment] = []
        for index in range(len(points) - 1):
            start = points[index]
            end = points[index + 1]
            from_lat, from_lng = float(start["lat"]), float(start["lng"])
            to_lat, to_lng = float(end["lat"]), float(end["lng"])
            distance = int(round(distance_meters(from_lat, from_lng, to_lat, to_lng)))
            walk_minutes = walk_minutes_between(from_lat, from_lng, to_lat, to_lng)
            warnings: list[str] = []
            links: list[ExternalNavigationLink] = []
            if distance < _MIN_SEGMENT_DISTANCE_M:
                warnings.append("segment_too_short_for_external_navigation")
            else:
                links = [
                    ExternalNavigationLink(
                        provider="yandex_maps",
                        mode="segment",
                        label="Пешком в Яндекс Картах",
                        web_url=_yandex_segment_url(from_lat, from_lng, to_lat, to_lng),
                        is_primary=True,
                    ),
                    ExternalNavigationLink(
                        provider="2gis",
                        mode="segment",
                        label="Пешком в 2ГИС",
                        web_url=_two_gis_segment_web_url(from_lat, from_lng, to_lat, to_lng),
                    ),
                ]
            segments.append(
                ExternalNavigationSegment(
                    from_index=int(start["index"]),
                    to_index=int(end["index"]),
                    from_place_id=_text(start.get("place_id")),
                    to_place_id=_text(end.get("place_id")),
                    from_title=_text(start.get("title")),
                    to_title=_text(end.get("title")),
                    distance_m=distance,
                    walk_duration_min=walk_minutes,
                    links=links,
                    warnings=warnings,
                )
            )
        return segments

    def _full_route(self, points: list[dict[str, object]]) -> ExternalNavigationFullRoute:
        if len(points) < 2:
            return ExternalNavigationFullRoute(available=False, reason="not_enough_points")
        if len(points) > _MAX_FULL_ROUTE_POINTS:
            return ExternalNavigationFullRoute(available=False, reason="too_many_points_for_stable_full_route")
        url = _yandex_full_route_url(points)
        if len(url) > _MAX_FULL_ROUTE_URL_LENGTH:
            return ExternalNavigationFullRoute(available=False, reason="url_too_long")
        return ExternalNavigationFullRoute(
            available=True,
            recommended=False,
            reason="preview_only_segment_navigation_is_primary",
            links=[
                ExternalNavigationLink(
                    provider="yandex_maps",
                    mode="full_route",
                    label="Посмотреть весь маршрут в Яндекс Картах",
                    web_url=url,
                    is_primary=True,
                )
            ],
        )


def build_external_navigation(points: list[object]) -> ExternalNavigationBlock:
    return ExternalNavigationService().build_for_points(points)


def record_external_navigation_event(
    db: Session,
    *,
    route_id: int | str,
    session_id: int | None,
    payload: ExternalNavigationEventRequest,
) -> bool:
    try:
        record_event(
            db,
            event_type=payload.event_type,
            payload={
                "route_id": str(route_id),
                "session_id": session_id,
                "provider": payload.provider,
                "mode": payload.mode,
                "from_index": payload.from_index,
                "to_index": payload.to_index,
                "platform": payload.platform,
                "client": payload.client,
                **payload.metadata,
            },
            city_slug=payload.city_slug,
            user_id=payload.user_id,
            commit=True,
        )
        return True
    except SQLAlchemyError:
        db.rollback()
        return False


def navigation_event_counts(db: Session) -> dict[str, int]:
    rows = db.query(ProductEvent).filter(ProductEvent.event_type.in_(NAVIGATION_EVENT_TYPES)).all()
    result: dict[str, int] = {event_type: 0 for event_type in NAVIGATION_EVENT_TYPES}
    for row in rows:
        result[row.event_type] = result.get(row.event_type, 0) + 1
    return result


NAVIGATION_EVENT_TYPES = (
    "external_navigation_opened",
    "external_navigation_fallback_used",
    "external_navigation_returned",
    "waypoint_confirmed",
    "waypoint_skipped",
    "route_completed",
    "route_abandoned",
)


def _to_waypoint(point: object) -> dict[str, object]:
    return {
        "index": int(_value(point, "position", _value(point, "ordering_index", 0)) or 0),
        "place_id": str(_value(point, "place_id", "") or ""),
        "title": _value(point, "place_title", None) or _value(point, "title", None),
        "lat": float(_value(point, "lat", 0.0) or 0.0),
        "lng": float(_value(point, "lng", 0.0) or 0.0),
    }


def _has_valid_coords(point: object) -> bool:
    try:
        lat = float(_value(point, "lat", 0.0))
        lng = float(_value(point, "lng", 0.0))
    except (TypeError, ValueError):
        return False
    return -90 <= lat <= 90 and -180 <= lng <= 180 and not (lat == 0 and lng == 0)


def _value(point: object, name: str, default: object = None) -> object:
    if isinstance(point, dict):
        return point.get(name, default)
    return getattr(point, name, default)


def _text(value: object) -> str | None:
    text = str(value or "").strip()
    return text or None


def _pct(value: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(value / total * 100.0, 1)


def _yandex_destination_url(lat: float, lng: float) -> str:
    return f"https://yandex.ru/maps/?pt={lng:.6f},{lat:.6f}&z=17&l=map"


def _yandex_segment_url(from_lat: float, from_lng: float, to_lat: float, to_lng: float) -> str:
    return f"https://yandex.ru/maps/?rtext={from_lat:.6f},{from_lng:.6f}~{to_lat:.6f},{to_lng:.6f}&rtt=pd"


def _yandex_full_route_url(points: list[dict[str, object]]) -> str:
    rtext = "~".join(f"{float(point['lat']):.6f},{float(point['lng']):.6f}" for point in points)
    return f"https://yandex.ru/maps/?rtext={rtext}&rtt=pd"


def _two_gis_destination_web_url(lat: float, lng: float) -> str:
    return f"https://2gis.ru/routeSearch/rsType/pedestrian/to/{lng:.6f},{lat:.6f}"


def _two_gis_segment_web_url(from_lat: float, from_lng: float, to_lat: float, to_lng: float) -> str:
    return f"https://2gis.ru/routeSearch/rsType/pedestrian/from/{from_lng:.6f},{from_lat:.6f}/to/{to_lng:.6f},{to_lat:.6f}"
