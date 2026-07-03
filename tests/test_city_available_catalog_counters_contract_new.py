from __future__ import annotations

from services.city_service import get_available_cities


def _by_slug(rows: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    return {str(row["slug"]): row for row in rows}


def test_available_city_counts_catalog_places_not_route_eligible_places_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="almaty", name="Алматы")
    place_factory(city_id=city.id, slug="museum", title="Museum", category="museum", is_route_eligible=True)
    place_factory(city_id=city.id, slug="park", title="Park", category="park", is_route_eligible=False)

    rows = _by_slug(get_available_cities(db_session))

    assert rows["almaty"]["places_count"] == 2


def test_available_city_counts_explicit_published_catalog_status_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="legacy", name="Legacy City")
    place_factory(
        city_id=city.id,
        slug="legacy-place",
        title="Legacy published place",
        category="museum",
        is_published=True,
        is_visible_in_catalog=True,
        is_active=True,
        publication_status="published",
    )

    rows = _by_slug(get_available_cities(db_session))

    assert rows["legacy"]["places_count"] == 1


def test_available_city_excludes_non_catalog_places_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="catalog", name="Catalog City")
    place_factory(city_id=city.id, slug="visible", title="Visible", category="museum")
    place_factory(city_id=city.id, slug="unpublished", title="Unpublished", category="museum", is_published=False)
    place_factory(city_id=city.id, slug="hidden", title="Hidden", category="museum", is_visible_in_catalog=False)
    place_factory(city_id=city.id, slug="inactive", title="Inactive", category="museum", is_active=False)

    rows = _by_slug(get_available_cities(db_session))

    assert rows["catalog"]["places_count"] == 1
