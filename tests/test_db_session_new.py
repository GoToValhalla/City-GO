import pytest

from db import dependencies, session


def test_engine_kwargs_include_pool_timeout_for_postgres_new(monkeypatch) -> None:
    monkeypatch.setattr(session.settings, "database_url", "postgresql+psycopg://db/prod")
    monkeypatch.setattr(session.settings, "db_pool_size", 12)
    monkeypatch.setattr(session.settings, "db_max_overflow", 6)
    monkeypatch.setattr(session.settings, "db_pool_timeout_seconds", 17)
    monkeypatch.setattr(session.settings, "db_pool_recycle_seconds", 900)

    assert session._engine_kwargs() == {
        "pool_pre_ping": True,
        "pool_size": 12,
        "max_overflow": 6,
        "pool_timeout": 17,
        "pool_recycle": 900,
    }


def test_engine_kwargs_skip_pool_options_for_sqlite_new(monkeypatch) -> None:
    monkeypatch.setattr(session.settings, "database_url", "sqlite:///:memory:")

    assert session._engine_kwargs() == {}


def test_get_db_rolls_back_and_closes_on_error_new(monkeypatch) -> None:
    fake_session = _FakeSession()
    monkeypatch.setattr(dependencies, "SessionLocal", lambda: fake_session)

    generator = dependencies.get_db()
    assert next(generator) is fake_session

    with pytest.raises(RuntimeError):
        generator.throw(RuntimeError("boom"))

    assert fake_session.rollback_called is True
    assert fake_session.close_called is True


class _FakeSession:
    def __init__(self) -> None:
        self.rollback_called = False
        self.close_called = False

    def rollback(self) -> None:
        self.rollback_called = True

    def close(self) -> None:
        self.close_called = True
