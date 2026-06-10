"""seed default global feature toggles

Revision ID: f9a2b3c4d5e6
Revises: e8f1a2b3c4d5
"""

from datetime import datetime
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f9a2b3c4d5e6"
down_revision: Union[str, None] = "e8f1a2b3c4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_DEFAULTS: tuple[tuple[str, bool, str], ...] = (
    ("web_app_enabled", True, "Публичный сайт доступен"),
    ("telegram_bot_enabled", True, "Бот отвечает пользователям"),
    ("maintenance_mode", False, "Публичный API недоступен"),
    ("route_generation_enabled", True, "Построение маршрутов"),
    ("route_planning_engine_enabled", True, "Route Planning Engine"),
    ("ai_layer_enabled", True, "AI-функции продукта"),
    ("place_verification_enabled", True, "Очередь проверки мест"),
    ("photo_moderation_enabled", True, "Очередь фото"),
    ("auto_import_enabled", True, "Фоновые импорты"),
    ("auto_enrichment_enabled", False, "Фоновое обогащение"),
    ("debug_mode", False, "Debug mode"),
)


def upgrade() -> None:
    now = datetime.utcnow()
    table = sa.table(
        "feature_toggles",
        sa.column("key", sa.String),
        sa.column("scope", sa.String),
        sa.column("scope_id", sa.String),
        sa.column("value_bool", sa.Boolean),
        sa.column("description", sa.String),
        sa.column("created_at", sa.DateTime),
        sa.column("updated_at", sa.DateTime),
    )
    conn = op.get_bind()
    for key, value, desc in _DEFAULTS:
        exists = conn.execute(
            sa.text("SELECT 1 FROM feature_toggles WHERE key=:k AND scope='global' AND scope_id IS NULL"),
            {"k": key},
        ).first()
        if exists:
            continue
        op.bulk_insert(table, [{"key": key, "scope": "global", "scope_id": None, "value_bool": value, "description": desc, "created_at": now, "updated_at": now}])


def downgrade() -> None:
    conn = op.get_bind()
    for key, _, _ in _DEFAULTS:
        conn.execute(sa.text("DELETE FROM feature_toggles WHERE scope='global' AND key=:k"), {"k": key})
