from __future__ import annotations

from asyncio import CancelledError

import pytest

from db import dependencies


class FakeSession:
    def __init__(self) -> None:
        self.rollback_calls = 0
        self.close_calls = 0

    def rollback(self) -> None:
        self.rollback_calls += 1

    def close(self) -> None:
        self.close_calls += 1


def test_get_db_closes_without_rollback_on_success_new(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeSession()
    monkeypatch.setattr(dependencies, "SessionLocal", lambda: fake)

    generator = dependencies.get_db()

    assert next(generator) is fake
    with pytest.raises(StopIteration):
        next(generator)

    assert fake.rollback_calls == 0
    assert fake.close_calls == 1


def test_get_db_rolls_back_and_closes_on_regular_exception_new(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeSession()
    monkeypatch.setattr(dependencies, "SessionLocal", lambda: fake)

    generator = dependencies.get_db()

    assert next(generator) is fake
    with pytest.raises(RuntimeError):
        generator.throw(RuntimeError("boom"))

    assert fake.rollback_calls == 1
    assert fake.close_calls == 1


def test_get_db_rolls_back_and_closes_on_cancelled_error_new(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = FakeSession()
    monkeypatch.setattr(dependencies, "SessionLocal", lambda: fake)

    generator = dependencies.get_db()

    assert next(generator) is fake
    with pytest.raises(CancelledError):
        generator.throw(CancelledError())

    assert fake.rollback_calls == 1
    assert fake.close_calls == 1
