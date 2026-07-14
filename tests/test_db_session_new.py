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


def test_postgres_connect_sets_idle_in_transaction_session_timeout_new(monkeypatch) -> None:
    """A worker connection SIGKILLed (OOM-kill, forced container stop)
    between claiming a queued job row (SELECT ... FOR UPDATE) and its very
    next commit leaves that transaction idle-in-transaction, holding the
    lock, until Postgres notices the dead connection — which without this
    setting can take a very long time (Postgres default
    tcp_keepalives_idle is 7200s). statement_timeout only bounds an
    executing statement; lock_timeout only bounds waiting to acquire a
    lock; neither bounds an idle transaction that already holds one."""
    monkeypatch.setattr(session.settings, "db_statement_timeout_ms", 15_000)
    monkeypatch.setattr(session.settings, "db_lock_timeout_ms", 5_000)
    monkeypatch.setattr(session.settings, "db_idle_in_transaction_session_timeout_ms", 30_000)

    executed: list[str] = []

    class _FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

        def execute(self, sql: str) -> None:
            executed.append(sql)

    class _FakeConnection:
        def cursor(self):
            return _FakeCursor()

    # The listener is a plain function registered via @event.listens_for and
    # is safe to call directly with a fake DBAPI connection.
    session.set_postgres_timeouts(_FakeConnection(), None)

    assert "SET statement_timeout = 15000" in executed
    assert "SET lock_timeout = 5000" in executed
    assert "SET idle_in_transaction_session_timeout = 30000" in executed


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
