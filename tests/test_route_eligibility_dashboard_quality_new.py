"""Expected-behavior tests for route eligibility dashboard quality gates."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from services.route_eligibility_dashboard import list_eligibility_places

F = TypeVar("F", bound=Callable[..., Any])

try:  # pragma: no cover - allure is optional in the current dependency set.
    import allure  # type: ignore
except ImportError:  # pragma: no cover
    class _AllureNoop:
        def epic(self, _title: str) -> Callable[[F], F]:
            return lambda func: func

        def feature(self, _title: str) -> Callable[[F], F]:
            return lambda func: func

        def story(self, _title: str) -> Callable[[F], F]:
            return lambda func: func

        def severity(self, _level: str) -> Callable[[F], F]:
            return lambda func: func

    allure = _AllureNoop()


@allure.epic("City Go Admin")
@allure.feature("Route Eligibility Dashboard")
@allure.story("High-quality bulk selection")
@allure.severity("critical")
def test_high_quality_readiness_filter_returns_only_publishable_places_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="quality-filter-city")
    good = place_factory(
        city_id=city.id,
        slug="real-museum",
        title="Краеведческий музей",
        category="museum",
        address="ул. Центральная, 1",
    )
    good.image_url = "https://example.test/museum.jpg"
    good.short_description = "Городской музей."
    good.opening_hours = {"daily": "10:00-18:00"}
    good.source_url = "https://example.test/museum"
    good.quality_tier = "gold"

    bad = place_factory(
        city_id=city.id,
        slug="osm-culture",
        title="Культурное место OSM 15446625",
        category="culture",
        address="ул. Безымянная, 2",
    )
    bad.image_url = "https://example.test/placeholder.jpg"
    bad.short_description = "Auto-generated placeholder."
    bad.opening_hours = {"daily": "10:00-18:00"}
    bad.source_url = "https://example.test/osm"
    bad.quality_tier = "gold"
    db_session.commit()

    items, total = list_eligibility_places(
        db_session,
        city_slug=city.slug,
        readiness="high_quality",
        quality="high",
        min_quality_score=75,
    )

    titles = {item["title"] for item in items}
    assert total == 1
    assert good.title in titles
    assert bad.title not in titles


@allure.epic("City Go Admin")
@allure.feature("Route Eligibility Dashboard")
@allure.story("Problem filters")
@allure.severity("normal")
def test_placeholder_readiness_filter_returns_only_auto_generated_names_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="placeholder-filter-city")
    place_factory(city_id=city.id, slug="real-park", title="Парк Победы", category="park")
    placeholder = place_factory(
        city_id=city.id,
        slug="park-osm",
        title="Парк OSM 1486707375",
        category="park",
    )

    items, total = list_eligibility_places(db_session, city_slug=city.slug, readiness="placeholder")

    assert total == 1
    assert items[0]["place_id"] == placeholder.id
    assert items[0]["primary_reason"] == "placeholder_title"


@allure.epic("City Go Admin")
@allure.feature("Route Eligibility Dashboard")
@allure.story("Pagination")
@allure.severity("normal")
def test_eligibility_pagination_returns_requested_slice_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="pagination-city")
    for index in range(5):
        place_factory(city_id=city.id, slug=f"place-{index}", title=f"Место {index}", category="museum")

    items, total = list_eligibility_places(db_session, city_slug=city.slug, limit=2, offset=2)

    assert total == 5
    assert len(items) == 2
    assert items[0]["title"] == "Место 2"
    assert items[1]["title"] == "Место 1"
