from __future__ import annotations

from functools import reduce


_WARNING_CODE_MESSAGES: dict[str, tuple[str, str, str, str]] = {
    "route_failed_no_places": (
        "route_failed_no_places",
        "error",
        "Не удалось собрать маршрут по выбранным параметрам.",
        "Измените время, интересы или стартовую точку.",
    ),
    "budget_too_tight": (
        "budget_too_tight",
        "error",
        "Слишком мало времени даже для одного места.",
        "Попробуйте выбрать время от 60 минут.",
    ),
    "budget_very_tight": (
        "budget_very_tight",
        "warning",
        "Времени хватает только на очень короткий маршрут.",
        "Увеличьте время, чтобы добавить больше мест.",
    ),
    "budget_fit_recovered_first_point": (
        "budget_fit_recovered_first_point",
        "warning",
        "Маршрут сохранён как короткий: первая точка полезна, но полный маршрут не влез во время.",
        "Увеличьте время или выберите старт ближе к местам.",
    ),
    "route_trimmed_by_budget": (
        "route_trimmed_by_budget",
        "info",
        "Часть мест убрана, чтобы маршрут уложился во время.",
        "Увеличьте время или добавьте место вручную.",
    ),
    "route_underfilled_by_budget": (
        "route_underfilled_by_budget",
        "info",
        "Маршрут использует меньше половины выбранного времени.",
        "Можно добавить ещё место вручную.",
    ),
    "route_short_due_to_time_budget": (
        "route_short_due_to_time_budget",
        "info",
        "Маршрут получился коротким из-за выбранного времени.",
        "Увеличьте время, если хотите добавить больше мест.",
    ),
    "route_short_due_to_low_place_density": (
        "route_short_due_to_low_place_density",
        "warning",
        "Подходящих точек для длинного маршрута пока мало.",
        "Попробуйте расширить интересы или добавить место вручную.",
    ),
    "some_places_have_no_address": (
        "some_places_have_no_address",
        "warning",
        "У части мест нет точного адреса.",
        "Ориентируйтесь по карте и координатам точки.",
    ),
    "some_places_have_no_photo": (
        "some_places_have_no_photo",
        "info",
        "У части мест пока нет фото.",
        "Проверьте карточку места перед прогулкой.",
    ),
    "some_places_have_weak_description": (
        "some_places_have_weak_description",
        "info",
        "У части мест пока короткое описание.",
        "Используйте карту и карточки мест для проверки деталей.",
    ),
    "route_has_long_walk_segments": (
        "route_has_long_walk_segments",
        "warning",
        "В маршруте есть длинные переходы пешком.",
        "Посмотрите расстояния между точками перед стартом.",
    ),
    "route_built_without_selected_interests": (
        "route_built_without_selected_interests",
        "info",
        "Маршрут собран в авто-режиме без выбранных интересов.",
        "Выберите интересы, если хотите более тематическую прогулку.",
    ),
    "neutral_poi_added": (
        "neutral_poi_added",
        "info",
        "Добавлены нейтральные точки, чтобы маршрут был полезнее.",
        "Проверьте список точек и удалите лишнее.",
    ),
    "related_categories_added": (
        "related_categories_added",
        "info",
        "Добавлены близкие категории, потому что точных совпадений мало.",
        "Можно изменить интересы или пересобрать маршрут.",
    ),
    "selected_interests_have_no_exact_matches": (
        "selected_interests_have_no_exact_matches",
        "warning",
        "По выбранным интересам не нашлось точных совпадений.",
        "Попробуйте выбрать другие интересы.",
    ),
    "selected_interest_has_single_anchor": (
        "selected_interest_has_single_anchor",
        "info",
        "По интересу нашлась только одна сильная точка.",
        "Остальные точки подобраны рядом.",
    ),
    "route_budget_overflow_tolerated": (
        "route_budget_overflow_tolerated",
        "warning",
        "Маршрут немного выходит за выбранное время.",
        "Сократите маршрут или увеличьте время.",
    ),
    "route_builder_v2_removed_route_junk": (
        "route_builder_v2_removed_route_junk",
        "info",
        "Из маршрута убраны неподходящие сервисные точки.",
        "Проверьте итоговый список мест.",
    ),
    "route_builder_v2_insufficient_points": (
        "route_builder_v2_insufficient_points",
        "warning",
        "После проверки осталось мало подходящих точек.",
        "Добавьте место вручную или расширьте интересы.",
    ),
    "long_initial_transfer": (
        "long_initial_transfer",
        "warning",
        "До первой точки далеко идти.",
        "Выберите старт ближе к центру маршрута.",
    ),
    "budget_swallowed_by_transfer": (
        "budget_swallowed_by_transfer",
        "warning",
        "Переходы съедают слишком много времени маршрута.",
        "Выберите старт ближе к точкам или увеличьте время.",
    ),
}

_UNKNOWN_WARNING_MESSAGE = "Маршрут собран с ограничениями по данным."


def route_warning_copy(code: str) -> tuple[str, str, str, str] | None:
    return _WARNING_CODE_MESSAGES.get(str(code or "").strip())


def route_warning_message(code: str) -> str:
    mapped = route_warning_copy(code)
    return mapped[2] if mapped else _UNKNOWN_WARNING_MESSAGE


def user_warnings(final: object) -> list[dict[str, object]]:
    route_warnings = tuple(str(item) for item in getattr(final, "warnings", []) or [])
    time_ids = tuple(str(item) for item in getattr(final, "places_with_warnings", []) or [])
    return _unique([*_route_warning_items(route_warnings), *_time_warning_items(time_ids)])


def _route_warning_items(warnings: tuple[str, ...]) -> list[dict[str, object]]:
    return [_warning_from_text(text) for text in warnings if text.strip()]


def _time_warning_items(place_ids: tuple[str, ...]) -> list[dict[str, object]]:
    if not place_ids:
        return []
    return [_item("time", "warning",
                  "У части мест есть риск по времени работы.",
                  place_ids, "Откройте карточку места и проверьте часы перед визитом.")]


def _warning_from_text(text: str) -> dict[str, object]:
    normalized = text.strip()
    mapped = route_warning_copy(normalized)
    if mapped:
        kind, severity, message, hint = mapped
        return _item(kind, severity, message, (), hint)

    lowered = normalized.casefold()
    rules = (
        (("час", "распис"), "time", "info", "Уточните часы перед визитом."),
        (("сокращ", "бюджет"), "budget", "info", "Увеличьте время или нажмите «Добавить место»."),
        (("однотип", "категор"), "diversity", "info", "Добавьте ограничения или пересоберите маршрут."),
    )
    match = next(filter(lambda rule: _contains_any(lowered, rule[0]), rules), None)
    kind, severity, hint = (match[1], match[2], match[3]) if match else (
        "data", "warning", "Проверьте детали мест перед прогулкой.")
    return _item(kind, severity, normalized if not _is_raw_code(normalized) else _UNKNOWN_WARNING_MESSAGE, (), hint)


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    return any(needle in text for needle in needles)


def _item(kind: str, severity: str, message: str, place_ids: tuple[str, ...], hint: str) -> dict[str, object]:
    return {
        "type": _public_warning_type(kind),
        "severity": severity,
        "user_message": message,
        "affected_place_ids": list(place_ids),
        "action_hint": hint,
    }


def _public_warning_type(kind: str) -> str:
    text = str(kind or "").strip().casefold()
    if not text:
        return "data"
    if any(token in text for token in ("budget", "time")):
        return "budget"
    if any(token in text for token in ("walk", "transfer")):
        return "walk"
    if "interest" in text:
        return "interest"
    if any(token in text for token in ("photo", "address", "description", "data")):
        return "data"
    return "route"


def _is_raw_code(text: str) -> bool:
    return bool(text and text.replace("_", "").replace("-", "").isalnum() and ("_" in text or "-" in text))


def _unique(items: list[dict[str, object]]) -> list[dict[str, object]]:
    _, result = reduce(_append_unique, items, (set(), []))
    return result


def _append_unique(
    state: tuple[set[tuple[object, object]], list[dict[str, object]]],
    item: dict[str, object],
) -> tuple[set[tuple[object, object]], list[dict[str, object]]]:
    seen, result = state
    key = (item.get("type"), item.get("user_message"))
    return (seen, result) if key in seen else ({*seen, key}, [*result, item])
