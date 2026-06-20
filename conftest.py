"""Repository-wide pytest hooks for Allure metadata.

The hook adds a consistent Allure hierarchy without requiring every existing test
function to be edited by hand. Explicit markers still win for severity/run type.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

try:
    import allure
except ImportError:  # pragma: no cover - Allure is optional for local minimal runs.
    allure = None


def _feature_from_path(path: Path) -> str:
    """Map test file path to a stable Allure feature."""
    text = path.as_posix().lower()
    name = path.name.lower()
    if "route" in text or "recommendation" in text or "candidate_retrieval" in text:
        return "Routes"
    if "admin" in text:
        return "Admin"
    if "place" in text or "taxonomy" in text or "seed" in text:
        return "Places and Data"
    if "city" in text:
        return "Cities"
    if "verification" in text:
        return "Verification"
    if "user" in text or "profile" in text or "signals" in text:
        return "Users and Personalization"
    if "model" in text or "models" in text:
        return "Data Models"
    if "readiness" in name or "health" in name or "deploy" in name:
        return "Infrastructure"
    return "Backend"


def _severity_for_item(item: pytest.Item, feature: str) -> str:
    """Return Allure severity from pytest markers and feature."""
    if item.get_closest_marker("critical") is not None:
        return "critical"
    if feature in {"Routes", "Admin", "Infrastructure"}:
        return "critical"
    if item.get_closest_marker("integration") is not None:
        return "normal"
    return "minor" if item.get_closest_marker("unit") is not None else "normal"


def _run_type_for_item(item: pytest.Item) -> str:
    """Return smoke/regression marker for Allure tagging."""
    if item.get_closest_marker("smoke") is not None:
        return "smoke"
    if item.get_closest_marker("regression") is not None:
        return "regression"
    return os.getenv("CITY_GO_TEST_RUN_TYPE", "regression")


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item: pytest.Item) -> None:
    """Populate Allure dynamic labels for every pytest test."""
    if allure is None:
        return

    path = Path(str(item.fspath))
    feature = _feature_from_path(path)
    run_type = _run_type_for_item(item)
    severity = _severity_for_item(item, feature)
    markers = sorted(marker.name for marker in item.iter_markers())

    allure.dynamic.epic("City Go")
    allure.dynamic.feature(feature)
    allure.dynamic.story(item.name)
    allure.dynamic.suite(path.parent.as_posix())
    allure.dynamic.sub_suite(path.name)
    allure.dynamic.severity(severity)
    allure.dynamic.tag(run_type)
    allure.dynamic.tag(feature.lower().replace(" ", "_"))
    for marker in markers:
        allure.dynamic.tag(marker)

    allure.dynamic.parameter("test_file", path.as_posix(), excluded=True)
    allure.dynamic.parameter("run_type", run_type, excluded=True)
