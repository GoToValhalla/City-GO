from __future__ import annotations

from collections.abc import Sequence

from services.place_staleness_policy import is_needs_verification

NO_CANDIDATES_WARNING = "Не нашли мест рядом с выбранным стартом."
ALL_FILTERED_WARNING = "Найденные места не прошли ограничения маршрута."
NO_ROUTE_POINTS_WARNING = "Не удалось собрать маршрут из найденных мест."
MISSING_OPENING_HOURS_WARNING = "У части мест нет часов работы; время визита проверено приблизительно."
MALFORMED_OPENING_HOURS_WARNING = "У части мест некорректные часы работы; использована деградация."
STALE_PLACES_WARNING = "У части мест давно не проверялась актуальность; маршрут может требовать ручной проверки."


def candidate_warnings(candidates: Sequence[object]) -> list[str]:
    has_candidates = bool(candidates)
    return _unique(
        [
            NO_CANDIDATES_WARNING if not has_candidates else "",
            MISSING_OPENING_HOURS_WARNING if has_candidates and _has_missing_hours(candidates) else "",
            MALFORMED_OPENING_HOURS_WARNING if _has_opening_hours_issue(candidates) else "",
            STALE_PLACES_WARNING if _has_stale_places(candidates) else "",
        ]
    )


def filter_warnings(
    candidates: Sequence[object],
    filtered: Sequence[object],
) -> list[str]:
    return [ALL_FILTERED_WARNING] if candidates and not filtered else []


def assembly_warnings(
    filtered: Sequence[object],
    route: Sequence[object],
) -> list[str]:
    return [NO_ROUTE_POINTS_WARNING] if filtered and not route else []


def _has_missing_hours(candidates: Sequence[object]) -> bool:
    return any(
        getattr(candidate, "opening_hours", None) is None
        or getattr(candidate, "opening_hours_mode", None) == "estimated_default"
        for candidate in candidates
    )


def _has_opening_hours_issue(candidates: Sequence[object]) -> bool:
    return any(_has_issue(candidate) for candidate in candidates)


def _has_stale_places(candidates: Sequence[object]) -> bool:
    return any(is_needs_verification(candidate) for candidate in candidates)


def _has_issue(candidate: object) -> bool:
    validation = getattr(candidate, "validation", None)
    issues = validation.get("issues") if isinstance(validation, dict) else []
    return isinstance(issues, list) and any(_is_opening_hours_issue(issue) for issue in issues)


def _is_opening_hours_issue(issue: object) -> bool:
    return isinstance(issue, str) and issue.startswith("opening_hours_")


def _unique(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(filter(None, values)))
