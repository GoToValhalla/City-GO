"""Repository-wide pytest hooks for readable Allure metadata."""

from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

try:
    import allure
except ImportError:  # pragma: no cover - Allure is optional for local minimal runs.
    allure = None


def _feature_from_path(path: Path) -> str:
    """Map a test file to the product area an operator can act on."""
    text = path.as_posix().lower()
    name = path.name.lower()
    if "import" in text or "enrichment" in text or "source_" in text:
        return "Импорт и обогащение"
    if "route" in text or "recommendation" in text or "candidate_retrieval" in text:
        return "Маршруты"
    if "admin" in text:
        return "Админка"
    if "taxonomy" in text or "category" in text:
        return "Категории и taxonomy"
    if "place" in text or "seed" in text:
        return "Места и данные"
    if "city" in text:
        return "Города"
    if "verification" in text or "review_queue" in text:
        return "Проверка данных"
    if "user" in text or "profile" in text or "signals" in text:
        return "Пользователи и персонализация"
    if "model" in text or "models" in text:
        return "Модели данных"
    if "readiness" in name or "health" in name or "deploy" in name or "ci_" in name:
        return "Инфраструктура и CI"
    return "Backend"


def _human_test_name(name: str) -> str:
    """Turn technical pytest names into readable Allure titles."""
    value = re.sub(r"^test_", "", name)
    value = re.sub(r"_new$", "", value)
    value = value.replace("_", " ").strip()
    return value[:1].upper() + value[1:] if value else name


def _severity_for_item(item: pytest.Item, feature: str) -> str:
    if item.get_closest_marker("critical") is not None:
        return "critical"
    if feature in {"Маршруты", "Админка", "Инфраструктура и CI", "Импорт и обогащение"}:
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


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item: pytest.Item) -> None:
    """Populate a stable product hierarchy and actionable metadata."""
    if allure is None:
        return

    path = Path(str(item.fspath))
    feature = _feature_from_path(path)
    run_type = _run_type_for_item(item)
    severity = _severity_for_item(item, feature)
    markers = sorted(marker.name for marker in item.iter_markers())
    title = _human_test_name(item.name)

    allure.dynamic.title(title)
    allure.dynamic.description(
        f"Продуктовая область: {feature}\n\n"
        f"Технический тест: `{item.nodeid}`\n\n"
        "При падении смотрите exception, шаг теста и вложенные stdout/stderr."
    )
    allure.dynamic.epic("City GO")
    allure.dynamic.feature(feature)
    allure.dynamic.story(title)
    allure.dynamic.parent_suite("City GO")
    allure.dynamic.suite(feature)
    allure.dynamic.sub_suite(path.stem.removesuffix("_new").replace("test_", "").replace("_", " "))
    allure.dynamic.severity(severity)
    allure.dynamic.tag(run_type)
    allure.dynamic.tag(feature.lower().replace(" ", "_"))
    for marker in markers:
        allure.dynamic.tag(marker)

    allure.dynamic.label("test_file", path.as_posix())
    allure.dynamic.label("node_id", item.nodeid)
    allure.dynamic.parameter("run_type", run_type, excluded=True)
