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
        (("budget_too_tight",), "time_budget_too_tight"),
        (("budget_very_tight",), "not_enough_route_points"),
        (("route_trimmed_by_budget",), "not_enough_route_points"),
        (("route_failed_no_places",), "no_places_in_city"),
        (("selected_interests_have_no_exact_matches",), "interests_not_matched"),
        (("algorithm_error_many_eligible_places_no_route",), "filters_too_strict"),
        (("рядом", "старт"), "few_candidates_near_start"),
        (("огранич", "прошли"), "filters_too_strict"),
    )
    return next((reason for needles, reason in rules if _has_any(text, needles)), "not_enough_route_points")


def _has_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _expected_min(expected_stops: int) -> int:
    if expected_stops <= 3:
        return 2
    if expected_stops <= 4:
        return 3
    if expected_stops <= 6:
        return 5
    return 6
