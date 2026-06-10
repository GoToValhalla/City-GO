from __future__ import annotations


def route_status(total_places: int, expected_stops: int) -> str:
    if total_places <= 0:
        return "no_route"
    return "ready" if total_places >= _expected_min(expected_stops) else "partial_route"


def partial_reason(status: str, warnings: list[str]) -> str | None:
    if status == "ready":
        return None
    text = " ".join(warnings).casefold()
    rules = (
        (("рядом", "старт"), "few_candidates_near_start"),
        (("огранич", "прошли"), "filters_too_strict"),
    )
    return next((reason for needles, reason in rules if _has_any(text, needles)), "not_enough_route_points")


def _has_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _expected_min(expected_stops: int) -> int:
    return max(2, min(3, expected_stops))
