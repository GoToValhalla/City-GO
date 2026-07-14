"""Manual PostgreSQL production-regression lane.

These tests exercise real concurrent connections, row locking
(`FOR UPDATE SKIP LOCKED`), and PostgreSQL-specific behavior (JSONB) that
SQLite cannot correctly reproduce (SQLite has no real concurrent-writer
row locking model). They talk to a real PostgreSQL database via
db.session.SessionLocal / core.config.settings.database_url and use real
commits + explicit teardown DELETEs instead of the SQLite rollback-per-test
fixture in tests/conftest.py, because rollback-wrapped transactions cannot
model two independent connections racing for the same row.

This directory is intentionally OUTSIDE `testpaths = tests` in pytest.ini,
so it is never collected by the default `pytest tests/` run, CI, or any
automatic lane. It is invoked only by the manual
.github/workflows/postgres-integration.yml workflow, which points pytest
directly at this directory against a real postgres:16 service container.
"""
from __future__ import annotations

import os
import uuid
from typing import Generator

import pytest
from sqlalchemy.orm import Session

from core.config import settings

if not settings.database_url.startswith(("postgresql", "postgres")):
    pytest.exit(
        "tests_postgres_integration requires a real PostgreSQL DATABASE_URL "
        f"(got {settings.database_url!r}). Refusing to run — these tests use "
        "real commits and would corrupt a SQLite/dev database.",
        returncode=1,
    )

from db.session import SessionLocal  # noqa: E402  (import after the safety guard above)
from models.category import Category  # noqa: E402
from models.city import City  # noqa: E402
from models.city_admin_import_job import CityAdminImportJob  # noqa: E402
from models.city_import_scope import CityImportScope  # noqa: E402
from models.place import Place  # noqa: E402
from models.review_queue_item import ReviewQueueItem  # noqa: E402


def unique_slug(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


@pytest.fixture
def pg_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture
def pg_city(pg_session: Session):
    city = City(slug=unique_slug("pg-city"), name="PG Integration City", is_active=True, launch_status="published")
    pg_session.add(city)
    pg_session.commit()
    pg_session.refresh(city)
    yield city
    pg_session.query(ReviewQueueItem).filter(ReviewQueueItem.city_id == city.id).delete()
    pg_session.query(CityAdminImportJob).filter(CityAdminImportJob.city_id == city.id).delete()
    pg_session.query(CityImportScope).filter(CityImportScope.city_id == city.id).delete()
    pg_session.query(Place).filter(Place.city_id == city.id).delete()
    pg_session.query(City).filter(City.id == city.id).delete()
    pg_session.commit()


@pytest.fixture
def pg_category(pg_session: Session):
    code = unique_slug("pg-category")
    category = Category(code=code, name="PG Integration Category")
    pg_session.add(category)
    pg_session.commit()
    pg_session.refresh(category)
    yield category
    pg_session.query(Category).filter(Category.id == category.id).delete()
    pg_session.commit()


def make_published_place(pg_session: Session, *, city: City, category: Category, **overrides) -> Place:
    defaults = dict(
        city_id=city.id,
        category_id=category.id,
        slug=unique_slug("pg-place"),
        title="PG Integration Place",
        category=category.code,
        lat=54.9611,
        lng=20.4703,
        status="active",
        is_active=True,
        is_published=True,
        is_visible_in_catalog=True,
        is_route_eligible=True,
        is_searchable=True,
        publication_status="published",
    )
    defaults.update(overrides)
    place = Place(**defaults)
    pg_session.add(place)
    pg_session.commit()
    pg_session.refresh(place)
    return place
