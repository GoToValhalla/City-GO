"""
Тесты: Import Quality Gate + Route Eligibility Fix.

Покрывают:
1. Чистую функцию assess_import_quality (unit, без БД).
2. Кандидатов маршрута с is_route_eligible (интеграция с БД).
3. Сводку импорта (import summary counters).
"""

import pytest

from services.import_publication_gate import assess_import_quality


# ─── 1. High-quality place → auto_published ──────────────────────────────────

def test_high_quality_place_becomes_published() -> None:
    """Полные данные → AUTO_PUBLISH → is_published=True, is_visible_in_catalog=True."""
    decision = assess_import_quality(
        title="Кофейня Море",
        lat=54.96,
        lng=20.47,
        category="coffee",
        confidence=0.8,
        source="osm",
        address="ул. Ленина, 5",
    )
    assert decision.decision == "auto_publish"
    assert decision.is_published is True
    assert decision.is_visible_in_catalog is True
    assert decision.publication_status == "published"


# ─── 2. Route category → is_route_eligible ───────────────────────────────────

def test_route_category_becomes_route_eligible() -> None:
    """Категория из ROUTE_ELIGIBLE_CATEGORIES → is_route_eligible=True при полных данных."""
    # Статические категории: address не требуется
    for cat in ("park", "museum", "walk", "beach"):
        d = assess_import_quality(
            title="Test", lat=54.96, lng=20.47, category=cat,
            confidence=0.8, source="osm",
        )
        assert d.is_route_eligible is True, f"expected route_eligible for category={cat}"
    # Динамические категории: нужен адрес для auto_publish
    for cat in ("coffee", "bar"):
        d = assess_import_quality(
            title="Test", lat=54.96, lng=20.47, category=cat,
            confidence=0.8, source="osm", address="ул. Ленина, 1",
        )
        assert d.is_route_eligible is True, f"expected route_eligible for dynamic category={cat}"


# ─── 3. No coordinates → hidden ──────────────────────────────────────────────

def test_no_coordinates_becomes_hidden() -> None:
    """Отсутствие координат → hidden."""
    for lat, lng in [(None, None), (0.0, 0.0), (None, 20.47)]:
        d = assess_import_quality(
            title="Some Place", lat=lat, lng=lng, category="coffee",
            confidence=0.8, source="osm",
        )
        assert d.decision == "hidden", f"expected hidden for lat={lat} lng={lng}"
        assert d.is_published is False


# ─── 4. No title → hidden ────────────────────────────────────────────────────

def test_no_title_becomes_hidden() -> None:
    """Пустой или None title → hidden."""
    for title in (None, "", "   "):
        d = assess_import_quality(
            title=title, lat=54.96, lng=20.47, category="park",
            confidence=0.8, source="osm",
        )
        assert d.decision == "hidden", f"expected hidden for title={title!r}"


# ─── 5. Low confidence → needs_review ────────────────────────────────────────

def test_low_confidence_becomes_needs_review() -> None:
    """Confidence ниже порога AUTO_PUBLISH → needs_review."""
    d = assess_import_quality(
        title="Неизвестное место",
        lat=54.96,
        lng=20.47,
        category="walk",
        confidence=0.3,
        source="osm",
    )
    assert d.decision == "needs_review"
    assert d.is_published is False
    assert d.publication_status == "needs_review"


# ─── 6. No source → needs_review ─────────────────────────────────────────────

def test_no_source_becomes_needs_review() -> None:
    """source=None → needs_review (нет провенанса)."""
    d = assess_import_quality(
        title="Место без источника",
        lat=54.96,
        lng=20.47,
        category="museum",
        confidence=0.8,
        source=None,
    )
    assert d.decision == "needs_review"
    assert d.is_route_eligible is False


# ─── 7. needs_review place не в публичном каталоге ───────────────────────────

def test_needs_review_place_not_in_public_catalog(db_session, city_factory) -> None:
    """Место с publication_status=needs_review не попадает в публичный каталог."""
    from models.place import Place
    from services.place_public_visibility import public_place_conditions

    city = city_factory(slug="gate-catalog-test")
    place = Place(
        slug="needs-review-catalog",
        title="На проверке",
        city_id=city.id,
        lat=54.96,
        lng=20.47,
        category="coffee",
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
        .filter(*public_place_conditions())
        .filter(Place.slug == "needs-review-catalog")
        .all()
    )
    assert len(results) == 0


# ─── 8. needs_review place не в route candidates ─────────────────────────────

def test_needs_review_place_not_in_route_candidates(db_session, city_factory) -> None:
    """Место needs_review не попадает в route candidates."""
    from models.place import Place
    from services.place_public_visibility import public_route_place_conditions

    city = city_factory(slug="gate-route-test")
    place = Place(
        slug="needs-review-route",
        title="На проверке (маршрут)",
        city_id=city.id,
        lat=54.96,
        lng=20.47,
        category="park",
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
        .filter(Place.slug == "needs-review-route")
        .all()
    )
    assert len(results) == 0


# ─── 9. is_route_eligible=False исключает опубликованное место из маршрутов ──

def test_published_place_without_route_eligible_excluded(db_session, city_factory) -> None:
    """Опубликованное место с is_route_eligible=False не попадает в route candidates."""
    from models.place import Place
    from services.place_public_visibility import public_route_place_conditions

    city = city_factory(slug="gate-eligible-test")
    place = Place(
        slug="published-not-route-eligible",
        title="Опубликовано, но без route_eligible",
        city_id=city.id,
        lat=54.96,
        lng=20.47,
        category="hotel",
        is_published=True,
        is_visible_in_catalog=True,
        is_route_eligible=False,
        publication_status="published",
        is_active=True,
        status="active",
    )
    db_session.add(place)
    db_session.commit()

    results = (
        db_session.query(Place)
        .filter(*public_route_place_conditions())
        .filter(Place.slug == "published-not-route-eligible")
        .all()
    )
    assert len(results) == 0


# ─── 10. Existing published place остаётся видимым ───────────────────────────

def test_existing_published_place_remains_visible(db_session, city_factory) -> None:
    """Уже опубликованное место остаётся в публичном каталоге."""
    from models.place import Place
    from services.place_public_visibility import public_place_conditions

    city = city_factory(slug="gate-existing-test")
    place = Place(
        slug="existing-published-gate",
        title="Давно опубликованное",
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
        .filter(Place.slug == "existing-published-gate")
        .all()
    )
    assert len(results) == 1


# ─── 11. Import summary counts ────────────────────────────────────────────────

def test_import_summary_counts(db_session, city_factory) -> None:
    """Import summary возвращает корректные счётчики auto_published / needs_review / rejected."""
    from schemas.place_seed_item import PlaceSeedItem
    from schemas.place_taxonomy_payload import PlaceTaxonomyPayload
    from services.place_seed_import_service import import_place_seed_items

    city = city_factory(slug="summary-count-city")
    taxonomy = PlaceTaxonomyPayload(category="museum", tags=[])

    items = [
        # auto_publish: полные данные
        PlaceSeedItem(
            title="Хороший музей",
            slug="good-museum-summary",
            city_slug="summary-count-city",
            category="museum",
            confidence=0.8,
            source="osm",
            address="ул. Ленина, 1",
            lat=54.96,
            lng=20.47,
            taxonomy=taxonomy,
        ),
        # needs_review: нет источника
        PlaceSeedItem(
            title="Без источника",
            slug="no-source-summary",
            city_slug="summary-count-city",
            category="museum",
            confidence=0.8,
            source=None,
            lat=54.96,
            lng=20.47,
            taxonomy=taxonomy,
        ),
        # hidden: нет координат
        PlaceSeedItem(
            title="Без координат",
            slug="no-coords-summary",
            city_slug="summary-count-city",
            category="museum",
            confidence=0.8,
            source="osm",
            lat=None,
            lng=None,
            taxonomy=taxonomy,
        ),
    ]

    summary = import_place_seed_items(db_session, items, dry_run=False)

    assert summary.auto_published == 1
    assert summary.needs_review_count == 1
    assert summary.rejected_count == 1
    assert summary.created == 3
