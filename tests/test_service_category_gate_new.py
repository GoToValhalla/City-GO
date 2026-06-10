"""
Тесты: нетуристические категории (health/service) не попадают в tourist catalog.

Проверяют, что Import Quality Gate корректно классифицирует
health/service/utility места как needs_review.
"""

import pytest

from services.import_publication_gate import assess_import_quality


# ─── 1. health/service place не auto_publish ─────────────────────────────────

def test_health_place_not_auto_published() -> None:
    """Imported place с категорией health → needs_review, не auto_publish."""
    decision = assess_import_quality(
        title="Аптека Ромашка",
        lat=54.96,
        lng=20.47,
        category="health",
        confidence=0.8,
        source="osm",
        address="ул. Ленина, 10",
    )
    assert decision.decision == "needs_review"
    assert decision.reason == "non_tourist_category"


def test_service_place_not_auto_published() -> None:
    """Imported place с категорией service → needs_review, не auto_publish."""
    decision = assess_import_quality(
        title="Мастерская по ремонту",
        lat=54.96,
        lng=20.47,
        category="service",
        confidence=0.8,
        source="osm",
        address="пр. Победы, 3",
    )
    assert decision.decision == "needs_review"
    assert decision.reason == "non_tourist_category"


# ─── 2. health/service не visible_in_catalog ─────────────────────────────────

def test_health_place_not_visible_in_catalog() -> None:
    """health → is_visible_in_catalog=False."""
    decision = assess_import_quality(
        title="Клиника Здоровье",
        lat=54.96,
        lng=20.47,
        category="health",
        confidence=0.9,
        source="osm",
    )
    assert decision.is_published is False
    assert decision.is_visible_in_catalog is False
    assert decision.publication_status == "needs_review"


# ─── 3. health/service is_route_eligible=False ───────────────────────────────

def test_health_place_not_route_eligible() -> None:
    """health → is_route_eligible=False."""
    decision = assess_import_quality(
        title="Больница",
        lat=54.96,
        lng=20.47,
        category="health",
        confidence=0.8,
        source="osm",
    )
    assert decision.is_route_eligible is False


# ─── 4. health/service не в route candidates ─────────────────────────────────

def test_health_place_not_in_route_candidates(db_session, city_factory) -> None:
    """Место с needs_review+non_tourist не попадает в route candidates."""
    from models.place import Place
    from services.place_public_visibility import public_route_place_conditions

    city = city_factory(slug="service-cat-test")
    place = Place(
        slug="health-place-route-test",
        title="Аптека тест",
        city_id=city.id,
        lat=54.96,
        lng=20.47,
        category="health",
        is_published=False,
        is_visible_in_catalog=False,
        is_route_eligible=False,
        publication_status="needs_review",
        is_active=True,
        status="active",
    )
    db_session.add(place)
    db_session.commit()

    results = (
        db_session.query(Place)
        .filter(*public_route_place_conditions())
        .filter(Place.slug == "health-place-route-test")
        .all()
    )
    assert len(results) == 0


# ─── 5. Tourist category по-прежнему auto_publish ────────────────────────────

def test_tourist_category_still_auto_published() -> None:
    """Туристическая категория с хорошими данными → auto_publish."""
    for cat in ("museum", "park", "walk", "attraction", "beach"):
        decision = assess_import_quality(
            title="Туристическое место",
            lat=54.96,
            lng=20.47,
            category=cat,
            confidence=0.8,
            source="osm",
        )
        assert decision.decision == "auto_publish", f"expected auto_publish for {cat}"
        assert decision.is_published is True


# ─── 6. Existing published tourist place остаётся visible ────────────────────

def test_existing_tourist_place_remains_visible(db_session, city_factory) -> None:
    """Опубликованные туристические места остаются видны в каталоге."""
    from models.place import Place
    from services.place_public_visibility import public_place_conditions

    city = city_factory(slug="tourist-visible-test")
    place = Place(
        slug="tourist-museum-visible",
        title="Музей янтаря",
        city_id=city.id,
        lat=54.96,
        lng=20.47,
        category="museum",
        is_published=True,
        is_visible_in_catalog=True,
        is_route_eligible=True,
        publication_status="published",
        is_active=True,
        status="active",
    )
    db_session.add(place)
    db_session.commit()

    results = (
        db_session.query(Place)
        .filter(*public_place_conditions())
        .filter(Place.slug == "tourist-museum-visible")
        .all()
    )
    assert len(results) == 1


# ─── 7. Import summary считает service как needs_review ──────────────────────

def test_import_summary_counts_service_as_needs_review(db_session, city_factory) -> None:
    """health/service места учитываются в needs_review_count сводки импорта."""
    from schemas.place_seed_item import PlaceSeedItem
    from schemas.place_taxonomy_payload import PlaceTaxonomyPayload
    from services.place_seed_import_service import import_place_seed_items

    city = city_factory(slug="service-summary-city")
    taxonomy = PlaceTaxonomyPayload(category="museum", tags=[])

    items = [
        PlaceSeedItem(
            title="Музей",
            slug="tourist-museum-svc",
            city_slug="service-summary-city",
            category="museum",
            confidence=0.8, source="osm",
            lat=54.96, lng=20.47,
            taxonomy=taxonomy,
        ),
        PlaceSeedItem(
            title="Аптека",
            slug="health-pharmacy-svc",
            city_slug="service-summary-city",
            category="health",
            confidence=0.8, source="osm",
            lat=54.96, lng=20.47,
            taxonomy=taxonomy,
        ),
        PlaceSeedItem(
            title="Мастерская",
            slug="service-workshop-svc",
            city_slug="service-summary-city",
            category="service",
            confidence=0.8, source="osm",
            lat=54.96, lng=20.47,
            taxonomy=taxonomy,
        ),
    ]

    summary = import_place_seed_items(db_session, items, dry_run=False)

    assert summary.auto_published == 1   # музей
    assert summary.needs_review_count == 2   # аптека + мастерская
    assert summary.rejected_count == 0
