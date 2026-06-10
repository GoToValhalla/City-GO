"""
Шаг 6 пайплайна: аннотация маршрута по времени — пешие минуты, прибытие/уход, time_status, time_warning.

Порядок точек не меняется, точки не удаляются и не заменяются.
"""

from datetime import datetime, timedelta
from typing import List

from schemas.merged_context import MergedContext
from services.route_assembly_service import RoutePoint
from services.time_aware_hours import apply_wait_gap, legacy_hours_status, time_status_and_warning
from services.time_aware_math import planned_visit_minutes, walk_minutes


class TimeAwareService:
    """
    Шаг 6: разметка времён прибытия и ухода.

    Вычисляет estimated_walk_minutes, estimated_arrival_time, estimated_departure_time,
    time_status и time_warning для каждой точки. Маршрут возвращается в том же порядке.
    """

    def apply(
        self,
        route: List[RoutePoint],
        ctx: MergedContext,
        start_time: datetime,
    ) -> List[RoutePoint]:

        if not route:
            return route

        clock = datetime.utcnow()
        current_time = start_time if start_time >= clock else clock

        for i, point in enumerate(route):
            if i == 0:
                lat0, lng0 = ctx.location
            else:
                prev = route[i - 1]
                lat0, lng0 = prev.lat, prev.lng

            walk_min = walk_minutes(lat0, lng0, point.lat, point.lng)
            point.estimated_walk_minutes = walk_min

            arrival = current_time + timedelta(minutes=walk_min)
            visit_min = planned_visit_minutes(point, ctx)
            departure = arrival + timedelta(minutes=visit_min)
            arrival, departure, wait_warning = apply_wait_gap(
                getattr(point, "opening_hours", None),
                arrival,
                visit_min,
            )

            point.estimated_arrival_time = arrival
            point.estimated_departure_time = departure
            point.arrival_time = arrival
            point.departure_time = departure

            status, warning = time_status_and_warning(
                getattr(point, "opening_hours", None),
                arrival,
                departure,
            )
            if wait_warning is not None and status == "ok":
                status, warning = "wait_before_opening", wait_warning
            point.time_status = status
            point.time_warning = warning

            # Совместимость с explainability / старыми полями
            point.hours_status = legacy_hours_status(status)
            point.is_valid = True

            current_time = departure

        return route
