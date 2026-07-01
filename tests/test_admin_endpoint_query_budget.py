from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import event
from sqlalchemy.orm import Session

import services.admin_extended_service as admin_extended_service
from services.admin_coverage_metrics import build_coverage_summary
from services.admin_metrics_service import build_metrics_summary
from services.admin_mobile_place_review import list_review_cities
from services.place_verification_service import get_place_verification_queue, place_verification_summary
from services.taxonomy_admin_service import list_categories


@contextmanager
def _select_statements(db_session: Session) -> Iterator[list[str]]:
    statements: list[str] = []
    bind = db_session.get_bind()

    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    event.listen(bind, "before_cursor_execute", before_cursor_execute)
    try:
        yield statements
    finally:
        event.remove(bind, "before_cursor_execute", before_cursor_execute)


def test_taxonomy_categories_uses_batched_place_counts(db_session, category_factory, place_factory):
    categories = [
        category_factory(code=f"tax-perf-{idx}", name=f"Tax Perf {idx}")
        for idx in range(5)
    ]
    for category in categories:
        for idx in range(3):
            place_factory(
                slug=f"tax-perf-place-{category.id}-{idx}",
                title=f"Tax Perf Place {category.id}-{idx}",
                category=category.code,
                category_id=category.id,
            )

    with _select_statements(db_session) as statements:
        payload = list_categories(
            db_session,
            search="tax-perf-",
            active=None,
            parent_id=None,
            route_policy=None,
            offset=0,
            limit=20,
        )

    assert payload["total"] == 5
    assert {item["places_count"] for item in payload["items"]} == {3}
    assert len(statements) <= 3


def test_admin_taxonomy_route_returns_manager_payload(client, category_factory):
    category_factory(code="tax-route-contract", name="Tax Route Contract")

    response = client.get("/admin/taxonomy/categories?search=tax-route-contract&limit=200")

    assert response.status_code == 200
    payload = response.json()
    assert "items" in payload
    assert "categories" not in payload
    assert payload["items"][0]["code"] == "tax-route-contract"


def test_place_verification_summary_and_queue_are_paged_in_database(db_session, city_factory, place_factory):
    city = city_factory(slug="verification-perf-city", name="Verification Perf")
    for idx in range(80):
        place = place_factory(
            slug=f"verification-perf-place-{idx}",
            title=f"Verification Perf Place {idx}",
            city_id=city.id,
            category="museum",
        )
        place.verification_status = "needs_recheck" if idx % 2 == 0 else "unverified"
        place.existence_confidence_score = idx % 40
        place.existence_confidence_level = "low"
        db_session.add(place)
    db_session.commit()

    with _select_statements(db_session) as summary_statements:
        summary = place_verification_summary(db_session, city_slug=city.slug)

    assert summary["queue_total"] == 80
    assert summary["needs_recheck"] == 40
    assert len(summary_statements) <= 1

    with _select_statements(db_session) as queue_statements:
        items, total = get_place_verification_queue(db_session, city_slug=city.slug, limit=10, offset=0)

    assert total == 80
    assert len(items) == 10
    assert len(queue_statements) <= 2


def test_admin_cities_batches_counters_and_latest_jobs(db_session, monkeypatch, city_factory, place_factory):
    monkeypatch.setattr(admin_extended_service, "_mark_stalled_imports_before_read", lambda db: None)
    cities = [
        city_factory(slug=f"city-list-perf-{idx}", name=f"City List Perf {idx}")
        for idx in range(5)
    ]
    for city in cities:
        for idx in range(2):
            place_factory(
                slug=f"city-list-perf-place-{city.id}-{idx}",
                title=f"City List Perf Place {city.id}-{idx}",
                city_id=city.id,
                category="museum",
                is_published=(idx == 0),
            )

    with _select_statements(db_session) as statements:
        items, total = admin_extended_service.get_admin_cities(db_session, limit=20, offset=0)

    rows_by_slug = {item["slug"]: item for item in items}
    assert total >= len(cities)
    for city in cities:
        assert rows_by_slug[city.slug]["places_total"] == 2
        assert rows_by_slug[city.slug]["places_published"] == 1
    assert len(statements) <= 5


def test_admin_coverage_summary_batches_city_metrics(db_session, city_factory, place_factory):
    cities = [city_factory(slug=f"coverage-perf-{idx}", name=f"Coverage Perf {idx}") for idx in range(5)]
    for city in cities:
        published = place_factory(city_id=city.id, slug=f"coverage-perf-published-{city.id}", is_published=True, image_url="https://img.test/a.jpg", address="ул. Мира, 1")
        published.short_description = "Описание"
        place_factory(city_id=city.id, slug=f"coverage-perf-hidden-{city.id}", is_published=False, image_url=None, address=None)
    db_session.commit()

    with _select_statements(db_session) as statements:
        items, total = build_coverage_summary(db_session, limit=5, offset=0)

    assert total >= len(cities)
    assert len(items) == 5
    assert len(statements) <= 6


def test_telegram_moderation_city_list_batches_counts(db_session, city_factory, place_factory):
    cities = [city_factory(slug=f"moderation-perf-{idx}", name=f"Moderation Perf {idx}") for idx in range(4)]
    for city in cities:
        place_factory(city_id=city.id, publication_status="needs_review")
        place_factory(city_id=city.id, publication_status="rejected")
        place_factory(city_id=city.id, publication_status="published")
    db_session.commit()

    with _select_statements(db_session) as statements:
        payload = list_review_cities(db_session)

    assert payload["total"] >= len(cities)
    assert len(statements) <= 2


def test_admin_metrics_summary_uses_compact_aggregates(db_session, place_factory):
    place_factory(slug="metrics-summary-a", is_published=True, image_url=None, address=None)
    place_factory(slug="metrics-summary-b", is_published=False, image_url="https://img.test/b.jpg", address="ул. Мира, 2")
    db_session.commit()

    with _select_statements(db_session) as statements:
        payload = build_metrics_summary(db_session)

    assert payload["places_total"] >= 2
    assert len(statements) <= 4
