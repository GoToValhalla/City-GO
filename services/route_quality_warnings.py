from functools import reduce

from services.route_assembly_service import RoutePoint

DIVERSITY_WARNING = "Маршрут получился однотипным; нужно расширить набор категорий."
SHORT_ROUTE_WARNING = "Маршрут короче ожидаемого: не хватило подходящих точек."


def route_quality_warnings(
    route: list[RoutePoint],
    expected_stops: int,
) -> list[str]:
    return _unique(
        [
            DIVERSITY_WARNING if _is_low_diversity(route) else "",
            SHORT_ROUTE_WARNING if _is_short_route(route, expected_stops) else "",
        ]
    )


def _is_low_diversity(route: list[RoutePoint]) -> bool:
    if len(route) < 3:
        return False
    counts = reduce(_count_category, route, {})
    dominant = max(counts.values()) if counts else 0
    return dominant == len(route) or dominant / len(route) >= 0.75


def _is_short_route(route: list[RoutePoint], expected_stops: int) -> bool:
    return bool(route) and len(route) < max(2, expected_stops // 2)


def _count_category(counts: dict[str, int], point: RoutePoint) -> dict[str, int]:
    category = str(getattr(point, "category", "") or "unknown")
    return {**counts, category: counts.get(category, 0) + 1}


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(filter(None, values)))
