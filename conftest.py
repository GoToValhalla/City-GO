"""Repository-wide pytest hooks for readable Allure reports."""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

try:
    import allure
except ImportError:  # pragma: no cover
    allure = None


def _hierarchy_from_path(path: Path) -> tuple[str, str]:
    text = path.as_posix().lower()
    name = path.name.lower()
    if "import" in text or "enrichment" in text or "source_" in text:
        return "Платформа данных", "Импорт и обогащение"
    if "taxonomy" in text or "category" in text:
        return "Платформа данных", "Категории и taxonomy"
    if "verification" in text or "review_queue" in text or "quality" in text:
        return "Платформа данных", "Качество и проверка данных"
    if "route" in text or "recommendation" in text or "candidate_retrieval" in text:
        return "Маршруты", "Построение и прохождение маршрута"
    if "admin" in text:
        return "Операционный центр", "Админка"
    if "place" in text or "seed" in text or "nearby" in text or "open_now" in text:
        return "Каталог мест", "Поиск и карточки мест"
    if "city" in text or "destination" in text:
        return "Территории", "Города и регионы"
    if "telegram" in text:
        return "Каналы", "Telegram"
    if "user" in text or "profile" in text or "signals" in text:
        return "Пользователи", "Профили и персонализация"
    if "model" in text or "models" in text:
        return "Платформа данных", "Модели данных"
    if "readiness" in name or "health" in name or "deploy" in name or "ci_" in name:
        return "Платформа", "Инфраструктура и CI"
    return "Платформа", "Backend"


def _human_test_name(name: str, feature: str) -> str:
    value = re.sub(r"^test_", "", name)
    value = re.sub(r"_new$", "", value)
    replacements = {
        "creates": "создаёт", "create": "создание", "updates": "обновляет", "update": "обновление",
        "deletes": "удаляет", "delete": "удаление", "returns": "возвращает", "rejects": "отклоняет",
        "allows": "разрешает", "blocks": "блокирует", "keeps": "сохраняет", "uses": "использует",
        "when": "когда", "without": "без", "with": "с", "missing": "отсутствует", "invalid": "невалидный",
        "valid": "валидный", "empty": "пустой", "failed": "ошибка", "success": "успех", "is": "",
        "not": "не", "and": "и", "or": "или", "for": "для", "from": "из", "to": "в",
    }
    words = [replacements.get(word, word) for word in value.split("_")]
    readable = " ".join(word for word in words if word).strip()
    readable = readable[:1].upper() + readable[1:] if readable else "технический сценарий"
    return f"{feature}: {readable}"


def _severity_for_item(item: pytest.Item, epic: str) -> str:
    if item.get_closest_marker("critical") is not None:
        return "critical"
    if epic in {"Маршруты", "Операционный центр", "Платформа данных"}:
        return "critical"
    if item.get_closest_marker("integration") is not None:
        return "normal"
    return "minor" if item.get_closest_marker("unit") is not None else "normal"


def _run_type_for_item(item: pytest.Item) -> str:
    if item.get_closest_marker("smoke") is not None:
        return "smoke"
    if item.get_closest_marker("regression") is not None:
        return "regression"
    return os.getenv("CITY_GO_TEST_RUN_TYPE", "regression")


def _set_metadata(item: pytest.Item) -> None:
    path = Path(str(item.fspath))
    epic, feature = _hierarchy_from_path(path)
    run_type = _run_type_for_item(item)
    markers = sorted(marker.name for marker in item.iter_markers())
    explicit_title = getattr(item.obj, "__allure_display_name__", None)
    if not explicit_title:
        allure.dynamic.title(_human_test_name(item.name, feature))
    allure.dynamic.epic(epic)
    allure.dynamic.feature(feature)
    allure.dynamic.parent_suite(epic)
    allure.dynamic.suite(feature)
    allure.dynamic.sub_suite(path.stem.removesuffix("_new").replace("test_", "").replace("_", " "))
    allure.dynamic.severity(_severity_for_item(item, epic))
    allure.dynamic.tag(run_type)
    for marker in markers:
        allure.dynamic.tag(marker)
    allure.dynamic.label("test_file", path.as_posix())
    allure.dynamic.label("node_id", item.nodeid)
    allure.dynamic.parameter("run_type", run_type, excluded=True)


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_setup(item: pytest.Item):
    if allure is None:
        yield
        return
    _set_metadata(item)
    with allure.step("Подготовка тестового окружения"):
        yield


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item: pytest.Item):
    if allure is None:
        yield
        return
    with allure.step("Выполнение проверки"):
        yield


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_teardown(item: pytest.Item):
    if allure is None:
        yield
        return
    with allure.step("Очистка тестового окружения"):
        yield


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item: pytest.Item, call: pytest.CallInfo):
    outcome = yield
    report = outcome.get_result()
    if allure is None or report.passed:
        return
    phase_labels = {"setup": "Подготовка тестового окружения", "call": "Выполнение проверки", "teardown": "Очистка тестового окружения"}
    phase = phase_labels.get(report.when, report.when)
    allure.dynamic.label("failed_phase", phase)
    allure.attach(
        f"Тест: {item.nodeid}\nФаза: {phase}\n\n{report.longreprtext}",
        name=f"Падение на шаге: {phase}",
        attachment_type=allure.attachment_type.TEXT,
    )
