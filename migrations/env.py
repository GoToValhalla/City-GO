from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context
from core.config import settings
from db.base import Base
import models.category  # noqa: F401
import models.city  # noqa: F401
import models.city_start_point  # noqa: F401
import models.city_candidate  # noqa: F401
import models.city_admin_import_job  # noqa: F401
import models.city_import_job  # noqa: F401
import models.city_import_scope  # noqa: F401
import models.city_scope_import_state  # noqa: F401
import models.collection  # noqa: F401
import models.collection_place  # noqa: F401
import models.country  # noqa: F401
import models.data_foundation  # noqa: F401
import models.import_batch  # noqa: F401
import models.import_job_step  # noqa: F401
import models.place  # noqa: F401
import models.place_field_confidence  # noqa: F401
import models.place_image  # noqa: F401
import models.place_photo_candidate  # noqa: F401
import models.place_discovery_request  # noqa: F401
import models.place_import_event  # noqa: F401
import models.place_schedule  # noqa: F401
import models.place_scope_link  # noqa: F401
import models.place_source_presence  # noqa: F401
import models.place_tag  # noqa: F401
import models.place_verification_task  # noqa: F401
import models.region  # noqa: F401
import models.route  # noqa: F401
import models.route_build_event  # noqa: F401
import models.route_draft  # noqa: F401
import models.route_place  # noqa: F401
import models.review_queue_item  # noqa: F401
import models.source_observation  # noqa: F401
import models.tag  # noqa: F401
import models.telegram_user_context  # noqa: F401
import models.user_signal  # noqa: F401

import os

config = context.config
_db_url = os.environ.get("DATABASE_URL") or settings.database_url
config.set_main_option("sqlalchemy.url", _db_url.replace("%", "%%"))

if config.config_file_name is not None and os.environ.get("ALEMBIC_SKIP_FILE_CONFIG") != "1":
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Запуск миграций в offline-режиме."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Запуск миграций в online-режиме."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
