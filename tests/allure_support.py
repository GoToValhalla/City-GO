"""Shared Allure helpers for readable functional scenarios."""

from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Iterator

import allure
import pytest


def scenario(title: str, *, epic: str, feature: str, story: str, severity: str = allure.severity_level.NORMAL):
    """Apply the complete product hierarchy to a functional test."""
    def decorate(function):
        function = allure.title(title)(function)
        function = allure.epic(epic)(function)
        function = allure.feature(feature)(function)
        function = allure.story(story)(function)
        function = allure.severity(severity)(function)
        return pytest.mark.allure_scenario(function)
    return decorate


@contextmanager
def given(text: str) -> Iterator[None]:
    with allure.step(f"Дано: {text}"):
        yield


@contextmanager
def when(text: str) -> Iterator[None]:
    with allure.step(f"Когда: {text}"):
        yield


@contextmanager
def then(text: str) -> Iterator[None]:
    with allure.step(f"Тогда: {text}"):
        yield


def attach_json(name: str, payload: object) -> None:
    """Attach structured diagnostics without leaking Python repr noise."""
    allure.attach(json.dumps(payload, ensure_ascii=False, indent=2, default=str), name=name, attachment_type=allure.attachment_type.JSON)


_TITLE_PHRASES = (
    ("dry_run", "пробный запуск"),
    ("available_cities", "доступные города"),
    ("route_engine", "построение маршрута"),
    ("route_build", "построение маршрута"),
    ("public_catalog", "публичный каталог"),
    ("draft_city", "черновой город"),
    ("published_city", "опубликованный город"),
    ("place_change", "изменение места"),
    ("city_status", "статус города"),
    ("city_import", "импорт города"),
    ("city_scope", "область импорта города"),
    ("total_report", "итоговый CI-отчёт"),
    ("frontend", "frontend"),
    ("backend", "backend"),
    ("admin", "админка"),
    ("telegram", "Telegram"),
    ("cities", "города"),
    ("city", "город"),
    ("places", "места"),
    ("place", "место"),
    ("routes", "маршруты"),
    ("route", "маршрут"),
    ("import", "импорт"),
    ("enrichment", "обогащение"),
    ("publish", "публикация"),
    ("unpublish", "снятие с публикации"),
    ("visibility", "видимость"),
    ("catalog", "каталог"),
    ("registry", "реестр"),
    ("available", "доступный"),
    ("bypasses", "обходит"),
    ("bypass", "обходит"),
    ("keeps", "сохраняет"),
    ("kept", "сохраняется"),
    ("rejects", "отклоняет"),
    ("reject", "отклоняет"),
    ("allows", "разрешает"),
    ("allow", "разрешает"),
    ("shows", "показывает"),
    ("show", "показывает"),
    ("uses", "использует"),
    ("use", "использует"),
    ("builds", "строит"),
    ("build", "строит"),
    ("creates", "создаёт"),
    ("create", "создаёт"),
    ("updates", "обновляет"),
    ("update", "обновляет"),
    ("fails", "завершается ошибкой"),
    ("failure", "ошибка"),
    ("error", "ошибка"),
    ("status", "статус"),
    ("test", "проверка"),
    ("new", ""),
)


def readable_test_title(name: str) -> str:
    """Build a stable human title for tests without an explicit Allure title."""

    value = str(name or "").removeprefix("test_").removesuffix("_new")
    if not value:
        return "Проверка без названия"

    for source, target in _TITLE_PHRASES:
        value = value.replace(source, target)
    value = " ".join(part for part in value.replace("_", " ").split() if part)
    if value.startswith("tm "):
        value = value.replace("tm ", "TM-", 1)
    return f"Проверка: {value[:1].upper() + value[1:]}" if value else "Проверка без названия"
