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

# Concurrent FOR UPDATE races need more than the production 5s lock_timeout.
os.environ.setdefault("DB_LOCK_TIMEOUT_MS", "30000")

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
    from sqlalchemy import text

    from models.place_publication_transition import PlacePublicationTransition

    pg_session.rollback()
    place_ids = [row[0] for row in pg_session.query(Place.id).filter(Place.city_id == city.id).all()]
    if place_ids:
        pg_session.query(ReviewQueueItem).filter(ReviewQueueItem.place_id.in_(place_ids)).delete(
            synchronize_session=False
        )
    from models.user_route_state_registry import UserRouteStateRegistry

    pg_session.query(UserRouteStateRegistry).filter(UserRouteStateRegistry.city_id == city.id).delete(
        synchronize_session=False
    )
    pg_session.query(ReviewQueueItem).filter(ReviewQueueItem.city_id == city.id).delete()
    pg_session.query(CityAdminImportJob).filter(CityAdminImportJob.city_id == city.id).delete()
    pg_session.query(CityImportScope).filter(CityImportScope.city_id == city.id).delete()
    if place_ids:
        try:
            pg_session.execute(text("ALTER TABLE place_publication_transitions DISABLE TRIGGER USER"))
            pg_session.query(PlacePublicationTransition).filter(
                PlacePublicationTransition.place_id.in_(place_ids)
            ).delete(synchronize_session=False)
            pg_session.query(Place).filter(Place.id.in_(place_ids)).delete(synchronize_session=False)
            pg_session.commit()
        finally:
            pg_session.execute(text("ALTER TABLE place_publication_transitions ENABLE TRIGGER USER"))
            pg_session.commit()
    pg_session.query(City).filter(City.id == city.id).delete()
    pg_session.commit()


@pytest.fixture
def pg_category(pg_session: Session):
    """Reusable route-eligible category; code must be in ALLOWED_ROUTE_CATEGORIES."""
    existing = pg_session.query(Category).filter(Category.code == "museum").one_or_none()
    if existing is not None:
        yield existing
        return

    category = Category(
        code="museum",
        name="Museum",
        is_active=True,
        is_catalog_visible=True,
        is_searchable=True,
        is_route_eligible=True,
        route_policy="allowed_by_context",
        route_contexts=["tourist_walk"],
    )
    pg_session.add(category)
    pg_session.commit()
    pg_session.refresh(category)
    yield category
    # Shared taxonomy row — leave in place for subsequent tests.


def make_published_place(pg_session: Session, *, city: City, category: Category, **overrides) -> Place:
    defaults = dict(
        city_id=city.id,
        category_id=category.id,
        slug=unique_slug("pg-place"),
        title="PG Integration Place",
        category=category.code,
        canonical_category=category.code,
        lat=54.9611,
        lng=20.4703,
        status="active",
        lifecycle_status="active",
        quality_tier="silver",
        place_layer="tourist_catalog",
        route_policy="city_walking",
        tourist_eligible=True,
        transport_required=False,
        is_active=True,
        is_published=True,
        is_visible_in_catalog=True,
        is_route_eligible=True,
        is_searchable=True,
        publication_status="published",
        is_spam_poi=False,
        is_duplicate_suspected=False,
        critical_field_expired=False,
    )
    defaults.update(overrides)
    place = Place(**defaults)
    pg_session.add(place)
    pg_session.commit()
    pg_session.refresh(place)
    return place
