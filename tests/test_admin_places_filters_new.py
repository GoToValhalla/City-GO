"""Тесты фильтров и покрытия админки."""

try:
    import allure
except ModuleNotFoundError:  # pragma: no cover
    allure = None

from models.city import City
from models.place import Place
from services.admin_coverage_metrics import build_coverage_summary
from services.admin_place_update_service import update_admin_place_fields
from services.admin_places_filters import apply_place_filters
from services.admin_service import get_admin_places
from services.admin_taxonomy_service import admin_category_taxonomy

pytestmark = [allure.epic("Admin QA"), allure.feature("Places filters and quality gates")] if allure else []


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


def test_preset_no_photo_new(client, db_session) -> None:
    city = _seed_city(db_session)
    _seed_place(db_session, city, slug="no-photo", image_url=None)
    _seed_place(db_session, city, slug="with-photo", image_url="http://x/img.jpg")
    db_session.commit()
    items, total = get_admin_places(db_session, preset="no_photo")
    assert total == 1
    assert items[0].slug == "no-photo"


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

    updated = update_admin_place_fields(db_session, place.id, {"category": "park", "route_enabled": True}, actor="qa")

    assert updated is not None
    assert updated.category == "park"
    assert updated.canonical_category == "park"
    assert updated.is_route_eligible is True
    assert updated.route_exclusion_reason is None


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


def test_coverage_summary_api_new(client) -> None:
    response = client.get("/admin/coverage/summary")
    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert "total" in body
