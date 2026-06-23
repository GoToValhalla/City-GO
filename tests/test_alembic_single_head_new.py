"""
Инвариант Alembic: ровно один head, ровно один base, 44 ревизии.

Не требует подключения к БД — проверяет только структуру migrations/versions/.

Цель: поймать новую ветку миграций без merge-ревизии до того,
как она попадёт в docker-compose migrate и сломает деплой.

Суффикс _new снимается после прогона (per testing rule).
"""
import unittest
from pathlib import Path


def _script():
    """Инициализирует ScriptDirectory из корневого alembic.ini."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    root = Path(__file__).resolve().parent.parent
    cfg = Config(str(root / "alembic.ini"))
    return ScriptDirectory.from_config(cfg)


class TestAlembicSingleHead(unittest.TestCase):
    """Структурные инварианты дерева миграций без подключения к ДБ."""

    def test_exactly_one_head(self) -> None:
        """Дерево миграций должно иметь ровно один head.

        Несколько heads означает, что появилась новая ветка без merge-ревизии.
        Это сломает `alembic upgrade head` в docker-compose (ambiguous target).
        """
        heads = _script().get_heads()
        self.assertEqual(
            len(heads),
            1,
            f"Ожидался ровно 1 head, найдено {len(heads)}: {heads}. "
            "Добавьте merge-миграцию (`alembic merge heads`) прежде чем деплоить.",
        )

    def test_known_head_revision(self) -> None:
        """Фиксирует текущий финальный head."""
        KNOWN_HEAD = "fb7e3c2a91d4"
        heads = _script().get_heads()
        self.assertIn(
            KNOWN_HEAD,
            heads,
            f"Известный head {KNOWN_HEAD} не найден. "
            f"Текущие heads: {heads}. "
            "Обновите KNOWN_HEAD в этом тесте при создании новой миграции.",
        )

    def test_exactly_one_base(self) -> None:
        """Дерево миграций должно иметь ровно один base (начало цепочки).

        Несколько bases означают несвязанные ветки истории.
        """
        script = _script()
        bases = [
            rev.revision
            for rev in script.walk_revisions()
            if rev.down_revision is None
        ]
        self.assertEqual(
            len(bases),
            1,
            f"Ожидался ровно 1 base, найдено {len(bases)}: {bases}.",
        )

    def test_known_base_revision(self) -> None:
        """Фиксирует текущий base (e48f13974bc8 — init_place_model)."""
        KNOWN_BASE = "e48f13974bc8"
        script = _script()
        bases = [
            rev.revision
            for rev in script.walk_revisions()
            if rev.down_revision is None
        ]
        self.assertIn(
            KNOWN_BASE,
            bases,
            f"Известный base {KNOWN_BASE} не найден. Текущие bases: {bases}.",
        )

    def test_total_revision_count(self) -> None:
        """Фиксирует общее число ревизий.

        Падение с другим числом — сигнал к ревью: добавлена или удалена миграция.
        Обновите EXPECTED_COUNT после добавления легитимной ревизии.
        """
        EXPECTED_COUNT = 44
        script = _script()
        total = sum(1 for _ in script.walk_revisions())
        self.assertEqual(
            total,
            EXPECTED_COUNT,
            f"Ожидалось {EXPECTED_COUNT} ревизий, найдено {total}. "
            "Обновите EXPECTED_COUNT если добавили или удалили миграцию.",
        )

    def test_env_metadata_covers_all_tables(self) -> None:
        """Проверяет, что target_metadata содержит таблицы, которые создают миграции.

        models/__init__.py импортирует все модели, поэтому любой
        `import models.*` в env.py регистрирует весь Base.metadata через side-effect.
        Тест защищает от случайного удаления __init__.py или его содержимого.
        """
        from db.base import Base
        import models  # noqa: F401 — импортирует models/__init__.py целиком

        expected_tables = {
            "places",
            "cities",
            "routes",
            "route_places",
            "route_sessions",
            "route_session_points",
            "route_drafts",
            "route_draft_points",
            "city_start_points",
            "admin_audit_logs",
            "place_verifications",
            "place_images",
            "telegram_user_contexts",
            "user_signals",
            "categories",
            "tags",
            "import_job_steps",
            "place_field_confidence",
            "place_photo_candidates",
            "review_queue_items",
            "bot_sessions",
            "bot_events",
        }
        actual_tables = set(Base.metadata.tables.keys())
        missing = expected_tables - actual_tables
        self.assertEqual(
            missing,
            set(),
            f"Таблицы отсутствуют в target_metadata: {missing}. "
            "Проверьте models/__init__.py.",
        )


if __name__ == "__main__":
    unittest.main()
