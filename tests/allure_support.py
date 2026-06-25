"""Shared Allure helpers for readable functional scenarios."""

from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Iterator

import allure


def scenario(
    title: str,
    *,
    epic: str,
    feature: str,
    story: str,
    severity: str = allure.severity_level.NORMAL,
):
    """Apply the complete product hierarchy to a functional test."""
    def decorate(function):
        function = allure.title(title)(function)
        function = allure.epic(epic)(function)
        function = allure.feature(feature)(function)
        function = allure.story(story)(function)
        function = allure.severity(severity)(function)
        return function

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
    allure.attach(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        name=name,
        attachment_type=allure.attachment_type.JSON,
    )
