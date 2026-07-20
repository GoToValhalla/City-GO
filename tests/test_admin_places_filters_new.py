"""Тесты фильтров и покрытия админки."""

from collections.abc import Callable
from typing import TypeVar

try:
    import allure
except ModuleNotFoundError:  # pragma: no cover
    allure = None

from models.city import City
from models.place import Place
from services.admin_coverage_metrics import build_coverage_summary
from services.admin_place_update_service import update_admin_place_fields
from services.admin_places_filters import _search_terms
from services.admin_service import get_admin_places
from services.admin_taxonomy_service import admin_category_taxonomy

F = TypeVar("F", bound=Callable[..., object])


def qa_title(title: str) -> Callable[[F], F]:
    if allure is None:
        return lambda fn: fn
    return allure.title(title)


def qa_story(story: str) -> Callable[[F], F]:
    if allure is None:
        return lambda fn: fn
    return allure.story(story)


def _seed_city(db, slug: str = "test-city") -> City:
    city = City(name="Test", slug=slug, country="RU", timezone="UTC", launch_status="published", is_active=True)
    db.add(city)
    db.flush()
    return city


def _seed_place(db, city: City, **kwargs) -> Place:
    defaults = dict(
        city_id=city.id, slug="place-1", title="Кафе", lat=1.0, lng=2.0,
        is_published=True, publication_status="published", image_url=None, address=None,
    )
    defaults.update(kwargs)
    place = Place(**defaults)
    db.add(place)
    db.flush()
    return place


@qa_story("Admin places filtering")
@qa_title("Фильтр no_photo показывает только места без фото")
def test_preset_no_photo_new(client, db_session) -> None:
    city = _seed_city(db_session)
    _seed_place(db_session, city, slug="no-photo", image_url=None)
    _seed_place(db_session, city, slug="with-photo", image_url="http://x/img.jpg")
    db_session.commit()
    items, total = get_admin_places(db_session, preset="no_photo")
    assert total == 1
    assert items[0].slug == "no-photo"


@qa_story("Route eligibility gates")
@qa_title("Фильтр маршрутов разделяет включенные и исключенные места")
def test_admin_places_route_filter_positive_and_negative_new(client, db_session) -> None:
    city = _seed_city(db_session, slug="route-city")
    _seed_place(db_session, city, slug="bank-disabled", title="Банк", category="service", is_route_eligible=False)
    _seed_place(db_session, city, slug="park-enabled", title="Парк", category="park", is_route_eligible=True)
    db_session.commit()

    enabled, enabled_total = get_admin_places(db_session, city_slug="route-city", route_eligible=True)
    disabled, disabled_total = get_admin_places(db_session, city_slug="route-city", route_eligible=False)

    assert enabled_total == 1
    assert enabled[0].slug == "park-enabled"
    assert disabled_total == 1
    assert disabled[0].slug == "bank-disabled"


@qa_story("Admin places search")
@qa_title("Поиск мест работает по названию, slug и адресу")
def test_admin_places_searches_title_slug_and_address_new(client, db_session) -> None:
    city = _seed_city(db_session, slug="search-city")
    _seed_place(db_session, city, slug="archeopark", title="Археопарк", category="service", address="Ханты-Мансийск")
    _seed_place(db_session, city, slug="mvd-office", title="МВД", category="service", address="Советская 1")
    db_session.commit()

    by_slug, slug_total = get_admin_places(db_session, city_slug="search-city", q="archeo")
    by_address, address_total = get_admin_places(db_session, city_slug="search-city", q="советская")
    missing, missing_total = get_admin_places(db_session, city_slug="search-city", q="несуществующее")

    assert slug_total == 1
    assert by_slug[0].title == "Археопарк"
    assert address_total == 1
    assert by_address[0].slug == "mvd-office"
    assert missing_total == 0
    assert missing == []


@qa_story("City-scoped taxonomy")
@qa_title("Счетчики категорий считаются в рамках выбранного города")
def test_category_taxonomy_counts_are_scoped_by_city_new(client, db_session) -> None:
    khanty = _seed_city(db_session, slug="khanty")
    arch = _seed_city(db_session, slug="arkhangelsk")
    _seed_place(db_session, khanty, slug="khanty-service", category="service")
    _seed_place(db_session, arch, slug="arch-park", category="park")
    db_session.commit()

    khanty_categories = {row["code"]: row for row in admin_category_taxonomy(db_session, city_slug="khanty")}
    arch_categories = {row["code"]: row for row in admin_category_taxonomy(db_session, city_slug="arkhangelsk")}

    assert khanty_categories["service"]["observed_count"] == 1
    assert khanty_categories["park"]["observed_count"] == 0
    assert arch_categories["service"]["observed_count"] == 0
    assert arch_categories["park"]["observed_count"] == 1


@qa_story("Manual category corrections")
@qa_title("Ручная смена категории синхронизирует canonical_category")
def test_manual_category_change_updates_canonical_category_new(client, db_session) -> None:
    city = _seed_city(db_session, slug="manual-category")
    place = _seed_place(
        db_session,
        city,
        slug="archeopark",
        title="Археопарк",
        category="service",
        canonical_category="service",
        is_route_eligible=False,
        route_exclusion_reason="service category",
    )
    db_session.commit()

    updated = update_admin_place_fields(db_session, place.id, {"category": "park"}, actor="qa")

    assert updated is not None
    assert updated.category == "park"
    assert updated.canonical_category == "park"
    assert updated.is_route_eligible is True
    assert updated.route_exclusion_reason is None


@qa_story("Coverage summary")
@qa_title("Coverage summary возвращает quality score по городу")
def test_coverage_summary_new(client, db_session) -> None:
    city = _seed_city(db_session, slug="cov-city")
    _seed_place(db_session, city, slug="p1", address="ул. Ленина", image_url="http://x/1.jpg", verification_status="verified")
    db_session.commit()
    items, total = build_coverage_summary(db_session)
    assert total >= 1
    row = next(r for r in items if r["city_slug"] == "cov-city")
    assert row["places_total"] == 1
    assert row["quality_score"] >= 0
    assert row["severity"] in ("green", "yellow", "red")


@qa_story("Coverage summary")
@qa_title("Coverage summary API возвращает items и total")
def test_coverage_summary_api_new(client) -> None:
    response = client.get("/admin/coverage/summary")
    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert "total" in body


def test_search_terms_postgresql_does_not_multiply_case_variants_new() -> None:
    """PostgreSQL ILIKE is already fully Unicode case-insensitive — the search
    must issue a single %term% clause, not 6 redundant case-variant duplicates."""
    terms = _search_terms("Советская", dialect="postgresql")
    assert terms == ("%Советская%",)


def test_search_terms_sqlite_keeps_case_variant_fallback_new() -> None:
    """SQLite's LIKE/ILIKE only case-folds ASCII, so the test-only fallback
    must still try multiple case variants to match stored Cyrillic/mixed-case data."""
    terms = _search_terms("советская", dialect="sqlite")
    assert "%советская%" in terms
    assert "%Советская%" in terms
    assert len(terms) > 1


def test_search_terms_empty_value_returns_no_terms_new() -> None:
    assert _search_terms("", dialect="postgresql") == ()
    assert _search_terms("   ", dialect="sqlite") == ()


def test_admin_places_search_matches_by_title_new(client, db_session) -> None:
    city = _seed_city(db_session, slug="search-title-city")
    _seed_place(db_session, city, slug="museum-place", title="Краеведческий музей", category="museum", address="ул. Музейная, 5")
    _seed_place(db_session, city, slug="cafe-place", title="Кафе Морское", category="cafe", address="ул. Портовая, 2")
    db_session.commit()

    items, total = get_admin_places(db_session, city_slug="search-title-city", q="музей")

    assert total == 1
    assert items[0].slug == "museum-place"


def test_admin_places_search_matches_by_slug_new(client, db_session) -> None:
    city = _seed_city(db_session, slug="search-slug-city")
    _seed_place(db_session, city, slug="unique-archeopark-slug", title="Место без совпадений в названии", category="park", address="ул. Парковая, 1")
    db_session.commit()

    items, total = get_admin_places(db_session, city_slug="search-slug-city", q="archeopark")

    assert total == 1
    assert items[0].slug == "unique-archeopark-slug"


def test_admin_places_search_matches_by_address_new(client, db_session) -> None:
    city = _seed_city(db_session, slug="search-address-city")
    _seed_place(db_session, city, slug="address-match-place", title="Место", category="service", address="ул. Балтийская, 10")
    db_session.commit()

    items, total = get_admin_places(db_session, city_slug="search-address-city", q="Балтийская")

    assert total == 1
    assert items[0].slug == "address-match-place"


def test_admin_places_search_cyrillic_case_insensitive_new(client, db_session) -> None:
    city = _seed_city(db_session, slug="search-cyrillic-city")
    _seed_place(db_session, city, slug="cyrillic-place", title="Ратуша", category="museum", address="Советская 1")
    db_session.commit()

    lower, lower_total = get_admin_places(db_session, city_slug="search-cyrillic-city", q="советская")
    upper, upper_total = get_admin_places(db_session, city_slug="search-cyrillic-city", q="СОВЕТСКАЯ")

    assert lower_total == 1
    assert upper_total == 1
    assert lower[0].slug == "cyrillic-place"
    assert upper[0].slug == "cyrillic-place"
