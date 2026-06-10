from __future__ import annotations


def point_phrase(count: int) -> str:
    return f"{count} {_point_word(count)}"


def warning_phrase(point_warning_count: int, total_warning_count: int) -> str:
    route_warning_count = max(0, total_warning_count - point_warning_count)
    if point_warning_count > 0 and route_warning_count > 0:
        return (
            f"Есть предупреждения по {_point_dative_phrase(point_warning_count)} "
            f"и {route_warning_count} {_warning_word(route_warning_count)} по маршруту."
        )
    if point_warning_count > 0:
        return f"Есть предупреждения по {_point_dative_phrase(point_warning_count)}."
    if route_warning_count > 0:
        return f"Есть {route_warning_count} {_warning_word(route_warning_count)} по маршруту."
    return ""


def _point_word(count: int) -> str:
    tail = count % 10
    teen = count % 100
    if tail == 1 and teen != 11:
        return "точку"
    if tail in {2, 3, 4} and teen not in {12, 13, 14}:
        return "точки"
    return "точек"


def _point_dative_phrase(count: int) -> str:
    if count == 1:
        return "1 точке"
    return f"{count} точкам"


def _warning_word(count: int) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return "предупреждение"
    if count % 10 in {2, 3, 4} and count % 100 not in {12, 13, 14}:
        return "предупреждения"
    return "предупреждений"
