from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.route_user_warnings import route_warning_copy, route_warning_message, user_warnings

ALLOWED_PUBLIC_TYPES = {"route", "data", "budget", "walk", "interest"}


@pytest.mark.parametrize(
    "code,expected_message",
    [
        ("route_failed_no_places", "Не удалось собрать маршрут по выбранным параметрам."),
        ("budget_too_tight", "Слишком мало времени даже для одного места."),
        ("budget_very_tight", "Времени хватает только на очень короткий маршрут."),
        ("budget_fit_recovered_first_point", "Маршрут сохранён как короткий: первая точка полезна, но полный маршрут не влез во время."),
        ("route_trimmed_by_budget", "Часть мест убрана, чтобы маршрут уложился во время."),
        ("route_underfilled_by_budget", "Маршрут использует меньше половины выбранного времени."),
        ("route_short_due_to_time_budget", "Маршрут получился коротким из-за выбранного времени."),
        ("route_short_due_to_low_place_density", "Подходящих точек для длинного маршрута пока мало."),
        ("some_places_have_no_address", "У части мест нет точного адреса."),
        ("some_places_have_no_photo", "У части мест пока нет фото."),
        ("some_places_have_weak_description", "У части мест пока короткое описание."),
        ("route_has_long_walk_segments", "В маршруте есть длинные переходы пешком."),
        ("route_built_without_selected_interests", "Маршрут собран в авто-режиме без выбранных интересов."),
        ("neutral_poi_added", "Добавлены нейтральные точки, чтобы маршрут был полезнее."),
        ("related_categories_added", "Добавлены близкие категории, потому что точных совпадений мало."),
        ("selected_interests_have_no_exact_matches", "По выбранным интересам не нашлось точных совпадений."),
        ("selected_interest_has_single_anchor", "По интересу нашлась только одна сильная точка."),
        ("route_budget_overflow_tolerated", "Маршрут немного выходит за выбранное время."),
        ("route_builder_v2_removed_route_junk", "Из маршрута убраны неподходящие сервисные точки."),
        ("route_builder_v2_insufficient_points", "После проверки осталось мало подходящих точек."),
        ("long_initial_transfer", "До первой точки далеко идти."),
        ("budget_swallowed_by_transfer", "Переходы съедают слишком много времени маршрута."),
    ],
)
def test_route_warning_message_maps_internal_codes_to_human_copy_new(code: str, expected_message: str) -> None:
    assert route_warning_message(code) == expected_message
    assert route_warning_copy(code) is not None


@pytest.mark.parametrize(
    "text",
    [
        "Не нашли мест рядом с выбранным стартом.",
        "У части мест нет часов работы; время визита проверено приблизительно.",
        "Маршрут сокращён, чтобы уложиться в выбранный бюджет времени.",
    ],
)
def test_route_warning_message_preserves_existing_human_copy_new(text: str) -> None:
    assert route_warning_message(text) == text


@pytest.mark.parametrize(
    "raw_code",
    [
        "unknown_internal_code",
        "route_builder_v3_new_private_reason",
        "quick_ignores_categories",
        "public_catalog_visible_route_eligible_only",
    ],
)
def test_route_warning_message_replaces_unknown_raw_codes_new(raw_code: str) -> None:
    assert route_warning_message(raw_code) == "Маршрут собран с ограничениями по данным."


def test_user_warnings_never_expose_raw_warning_type_or_message_new() -> None:
    final = SimpleNamespace(
        warnings=[
            "route_builder_v2_insufficient_points",
            "unknown_internal_code",
            "Не нашли мест рядом с выбранным стартом.",
            "Маршрут сокращён, чтобы уложиться в выбранный бюджет времени.",
        ],
        places_with_warnings=["1", "2"],
    )

    warnings = user_warnings(final)

    assert warnings
    assert {warning["type"] for warning in warnings} <= ALLOWED_PUBLIC_TYPES
    assert all("_" not in str(warning["type"]) for warning in warnings)
    assert all("unknown_internal_code" not in str(warning["user_message"]) for warning in warnings)
    assert all("route_builder_v2_insufficient_points" not in str(warning["user_message"]) for warning in warnings)
    assert any(warning["user_message"] == "После проверки осталось мало подходящих точек." for warning in warnings)
    assert any(warning["user_message"] == "Маршрут собран с ограничениями по данным." for warning in warnings)
    assert any(warning["type"] == "budget" for warning in warnings)


def test_user_warnings_deduplicates_same_public_warning_new() -> None:
    final = SimpleNamespace(
        warnings=["route_builder_v2_insufficient_points", "route_builder_v2_insufficient_points"],
        places_with_warnings=[],
    )

    warnings = user_warnings(final)

    assert warnings == [
        {
            "type": "route",
            "severity": "warning",
            "user_message": "После проверки осталось мало подходящих точек.",
            "affected_place_ids": [],
            "action_hint": "Добавьте место вручную или расширьте интересы.",
        }
    ]


def test_user_warnings_adds_time_warning_for_places_with_time_risk_new() -> None:
    final = SimpleNamespace(warnings=[], places_with_warnings=["10", "11"])

    warnings = user_warnings(final)

    assert warnings == [
        {
            "type": "budget",
            "severity": "warning",
            "user_message": "У части мест есть риск по времени работы.",
            "affected_place_ids": ["10", "11"],
            "action_hint": "Откройте карточку места и проверьте часы перед визитом.",
        }
    ]
