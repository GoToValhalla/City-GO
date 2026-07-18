from __future__ import annotations

import tempfile
from pathlib import Path

from sqlalchemy import create_engine, inspect

from db.base import Base
from tests.allure_support import title


@title("Фабрика published-place явно создаёт опубликованное видимое место")
def test_published_place_factory_sets_consistent_public_flags(published_place_factory) -> None:
    place = published_place_factory(slug="factory-published-place")
    assert place.is_active is True
    assert place.is_published is True
    assert place.is_visible_in_catalog is True
    assert place.is_searchable is True
    assert place.is_route_eligible is True
    assert place.publication_status == "published"


@title("Фабрика draft-place явно создаёт черновик без публичных флагов")
def test_draft_place_factory_sets_consistent_draft_flags(draft_place_factory) -> None:
    place = draft_place_factory(slug="factory-draft-place")
    assert place.is_active is True
    assert place.is_published is False
    assert place.is_visible_in_catalog is False
    assert place.is_searchable is False
    assert place.is_route_eligible is False
    assert place.publication_status == "draft"


@title("Фабрика manual-review-place отделяет ручную очередь от auto backlog")
def test_manual_review_place_factory_sets_explicit_manual_status(manual_review_place_factory) -> None:
    place = manual_review_place_factory(slug="factory-manual-place")
    assert place.is_published is False
    assert place.is_visible_in_catalog is False
    assert place.publication_status == "needs_review"


@title("Фабрика auto-backlog-place не создаёт ручную очередь")
def test_auto_backlog_place_factory_sets_non_manual_backlog_status(auto_backlog_place_factory) -> None:
    place = auto_backlog_place_factory(slug="factory-auto-backlog-place")
    assert place.is_published is False
    assert place.is_visible_in_catalog is False
    assert place.publication_status == "auto_backlog"


@title("Фабрика hidden-place создаёт скрытое неактивное место")
def test_hidden_place_factory_sets_consistent_hidden_flags(hidden_place_factory) -> None:
    place = hidden_place_factory(slug="factory-hidden-place")
    assert place.is_active is False
    assert place.is_published is False
    assert place.is_visible_in_catalog is False
    assert place.is_searchable is False
    assert place.is_route_eligible is False
    assert place.publication_status == "hidden"


@title("Metadata schema содержит критичные таблицы review/import/photo/publication")
def test_metadata_schema_contains_critical_tables() -> None:
    table_names = set(Base.metadata.tables)
    assert "review_queue_items" in table_names
    assert "city_admin_import_jobs" in table_names
    assert "place_photo_candidates" in table_names
    assert "place_publication_decisions" in table_names
    assert "place_publication_transitions" in table_names
    assert "admin_audit_logs" in table_names


@title("Тестовая БД включает критичные таблицы после create_all")
def test_test_database_contains_critical_tables(engine) -> None:
    tables = set(inspect(engine).get_table_names())
    assert "review_queue_items" in tables
    assert "city_admin_import_jobs" in tables
    assert "place_photo_candidates" in tables
    assert "place_publication_decisions" in tables
    assert "place_publication_transitions" in tables
    assert "admin_audit_logs" in tables


def _upgrade_temp_database() -> tuple[str, object]:
    from alembic import command
    from alembic.config import Config
    import os

    tmp_dir = tempfile.TemporaryDirectory()
    db_path = Path(tmp_dir.name) / "alembic_head_check.db"
    root = Path(__file__).resolve().parent.parent
    cfg = Config(str(root / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    previous = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    try:
        command.upgrade(cfg, "head")
    finally:
        if previous is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous
    return f"sqlite:///{db_path}", tmp_dir


@title("Alembic head создаёт publication schema, но не включает Phase 6 до verification")
def test_alembic_upgrade_head_defers_strict_publication_constraint() -> None:
    database_url, tmp_dir = _upgrade_temp_database()
    try:
        engine = create_engine(database_url)
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        checks = {item["name"] for item in inspector.get_check_constraints("places")}
        engine.dispose()
    finally:
        tmp_dir.cleanup()

    assert "place_publication_decisions" in tables
    assert "place_publication_transitions" in tables
    assert "ck_places_publication_reason_consistency" not in checks


@title("ReviewQueueItem schema допускает nullable job_id для не-import ручной очереди")
def test_review_queue_item_job_id_is_nullable_for_manual_items(engine) -> None:
    columns = {column["name"]: column for column in inspect(engine).get_columns("review_queue_items")}
    assert "job_id" in columns
    assert columns["job_id"]["nullable"] is True


@title("Place photo candidates имеет уникальность по place_id и image_url")
def test_place_photo_candidates_have_place_url_uniqueness() -> None:
    table = Base.metadata.tables["place_photo_candidates"]
    unique_columns = {
        tuple(column.name for column in constraint.columns)
        for constraint in table.constraints
        if constraint.__class__.__name__ == "UniqueConstraint"
    }
    assert ("place_id", "image_url") in unique_columns
