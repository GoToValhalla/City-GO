"""Regression for the empty-catalog defect: /api/cities/available previously
returned published cities with places_count > 0 (a looser catalogue counter)
even when /api/places/ would return zero places for that city, because the
counter and the real public place visibility filter used different
condition sets. get_available_cities must only advertise a city when
/api/places/ (services.place_public_visibility.admin_preview_place_conditions)
would actually return at least one place for it."""

from __future__ import annotations

from models.feature_toggle import FeatureToggle
from models.place import Place
from services.city_service import get_available_cities


def _slugs(db_session, **kwargs) -> set[str]:
    return {row["slug"] for row in get_available_cities(db_session, **kwargs)}


def _add_place(db_session, *, city_id: int, slug: str, **overrides) -> Place:
    defaults = dict(
        title="Место",
        lat=43.2,
        lng=76.9,
        is_active=True,
        is_published=True,
        is_visible_in_catalog=True,
        publication_status="published",
    )
    defaults.update(overrides)
    place = Place(city_id=city_id, slug=slug, **defaults)
    db_session.add(place)
    db_session.commit()
    return place


def test_published_city_with_zero_visible_places_is_excluded_new(db_session, city_factory) -> None:
    city_factory(slug="almaty", name="Алматы", is_active=True, launch_status="published")

    assert _slugs(db_session) == set()


def test_published_city_with_only_hidden_category_places_is_excluded_new(db_session, city_factory) -> None:
    """The catalogue counter intentionally counts hidden-category places (see
    city_service module docstring), but /api/places/ excludes them via
    canonical_category — a city whose only places are pharmacy/health/etc.
    must still be excluded."""
    city = city_factory(slug="almaty", name="Алматы", is_active=True, launch_status="published")
    _add_place(db_session, city_id=city.id, slug="almaty-pharmacy", canonical_category="pharmacy")
    _add_place(db_session, city_id=city.id, slug="almaty-health", canonical_category="health")

    assert _slugs(db_session) == set()


def test_published_city_with_only_service_only_places_is_excluded_new(db_session, city_factory) -> None:
    """internal_status='service_only' is a second /api/places/ exclusion gate
    the catalogue counter does not apply."""
    city = city_factory(slug="almaty", name="Алматы", is_active=True, launch_status="published")
    _add_place(db_session, city_id=city.id, slug="almaty-service", internal_status="service_only")

    assert _slugs(db_session) == set()


def test_city_with_visible_places_remains_available_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="almaty", name="Алматы", is_active=True, launch_status="published")
    place_factory(city_id=city.id, slug="almaty-museum", title="Музей", category="museum")

    assert _slugs(db_session) == {"almaty"}


def test_city_with_one_visible_and_many_hidden_places_remains_available_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="almaty", name="Алматы", is_active=True, launch_status="published")
    _add_place(db_session, city_id=city.id, slug="almaty-pharmacy", canonical_category="pharmacy")
    place_factory(city_id=city.id, slug="almaty-museum", title="Музей", category="museum")

    assert _slugs(db_session) == {"almaty"}


def test_admin_only_city_remains_excluded_even_with_visible_places_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="almaty", name="Алматы", is_active=True, launch_status="published")
    place_factory(city_id=city.id, slug="almaty-museum", title="Музей", category="museum")
    db_session.add(FeatureToggle(key="admin_only_city", scope="city", scope_id=city.slug, value_bool=True))
    db_session.commit()

    assert _slugs(db_session) == set()


def test_test_city_remains_excluded_even_with_visible_places_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="almaty", name="Алматы", is_active=True, launch_status="published")
    place_factory(city_id=city.id, slug="almaty-museum", title="Музей", category="museum")
    db_session.add(FeatureToggle(key="test_city", scope="city", scope_id=city.slug, value_bool=True))
    db_session.commit()

    assert _slugs(db_session) == set()


def test_draft_preview_still_shows_empty_city_new(db_session, city_factory) -> None:
    """include_draft=True is the admin/draft preview path (not the public
    /api/cities/available endpoint) and must not hide empty cities from
    operators who are actively building out a new city's catalogue."""
    city_factory(slug="almaty", name="Алматы", is_active=True, launch_status="draft")

    assert _slugs(db_session, include_draft=True) == {"almaty"}


def test_multiple_cities_only_non_empty_ones_available_new(db_session, city_factory, place_factory) -> None:
    empty_city = city_factory(slug="almaty", name="Алматы", is_active=True, launch_status="published")
    full_city = city_factory(slug="baku", name="Баку", is_active=True, launch_status="published")
    place_factory(city_id=full_city.id, slug="baku-museum", title="Музей", category="museum")

    assert _slugs(db_session) == {"baku"}
    assert empty_city.slug not in _slugs(db_session)
