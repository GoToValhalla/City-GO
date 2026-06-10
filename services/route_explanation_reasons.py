from __future__ import annotations


TEXT = {
    "interest": "Хорошо совпадает с выбранными интересами.",
    "time_context": "Подходит для выбранного времени дня.",
    "data_confidence": "Данные по месту выглядят достаточно надёжными.",
    "base_quality": "У места хорошо заполнены данные для маршрута.",
    "popularity_proxy": "У места есть признаки известности в открытых источниках.",
    "proximity": "Логично ложится в порядок прогулки рядом с предыдущей точкой.",
    "default": "Подходит под общий сценарий маршрута.",
}


def point_reason(point: object) -> tuple[str, str]:
    if _walk_minutes(point) <= 5 and _walk_minutes(point) > 0:
        return TEXT["proximity"], "proximity"
    key = _strongest_component(_breakdown(point))
    return TEXT.get(key, TEXT["default"]), key or "default"


def score_components(point: object) -> dict[str, float]:
    breakdown = _breakdown(point)
    keys = ("interest", "time_context", "data_confidence", "base_quality", "popularity_proxy")
    return {key: round(float(breakdown.get(key, 0.0) or 0.0), 3) for key in keys}


def data_notes(route: object) -> list[str]:
    points = list(getattr(route, "points", []) or [])
    return _unique([_point_data_note(point) for point in points] + list(getattr(route, "warnings", []) or []))


def _point_data_note(point: object) -> str:
    status = str(getattr(point, "time_status", "") or "")
    if status == "hours_unknown":
        return "У части мест часы работы неизвестны — уточните перед визитом."
    if status in {"closed_at_arrival", "closes_during_visit"}:
        return "У части мест есть риск по времени работы."
    return ""


def _strongest_component(breakdown: dict[str, float]) -> str:
    candidates = {key: float(breakdown.get(key, 0.0) or 0.0) for key in TEXT if key in breakdown}
    return max(candidates, key=candidates.get) if candidates else "default"


def _breakdown(point: object) -> dict[str, float]:
    raw = getattr(point, "scoring_breakdown", None)
    return raw if isinstance(raw, dict) else {}


def _walk_minutes(point: object) -> int:
    return int(getattr(point, "estimated_walk_minutes", 0) or 0)


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(filter(None, values)))
