"""Тесты route eligibility."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from models.city import City
from models.place import Place
from services.route_eligibility import (
    apply_route_eligible_filters,
    evaluate_place_route_eligibility,
    is_route_forbidden_category,
)

F = TypeVar("F", bound=Callable[..., Any])

try:  # pragma: no cover - allure may be absent in local CI dependencies.
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
@allure.feature("Route Eligibility Quality Gates")
def _place(**kwargs) -> Place:
    defaults = {
        "id": 1,
        "city_id": 1,
        "slug": "p1",
        "title": "Test",
        "lat": 54.96,
        "lng": 20.47,
        "category": "museum",
        "is_active": True,
        "status": "active",
        "is_published": True,
        "is_visible_in_catalog": True,
        "is_route_eligible": True,
    }
    defaults.update(kwargs)
    return Place(**defaults)


def test_forbidden_category_not_eligible_new() -> None:
    result = evaluate_place_route_eligibility(_place(category="pharmacy"))
    assert not result.eligible
    assert any("forbidden_category" in reason for reason in result.reasons)


def test_missing_coordinates_not_eligible_new() -> None:
    result = evaluate_place_route_eligibility(_place(lat=None, lng=None))
    assert not result.eligible
    assert "missing_coordinates" in result.reasons


def test_inactive_place_not_eligible_new() -> None:
    result = evaluate_place_route_eligibility(_place(is_active=False))
    assert not result.eligible
    assert "place_inactive" in result.reasons


def test_unpublished_place_not_eligible_new() -> None:
    result = evaluate_place_route_eligibility(_place(is_published=False))
    assert not result.eligible
    assert "place_not_published" in result.reasons


def test_route_eligible_false_not_eligible_new() -> None:
    result = evaluate_place_route_eligibility(_place(is_route_eligible=False))
    assert not result.eligible
    assert "route_eligible_false" in result.reasons


@allure.story("Placeholder names are blocked from routes")
@allure.severity("critical")
def test_placeholder_osm_title_not_eligible_new() -> None:
    result = evaluate_place_route_eligibility(_place(title="Культурное место OSM 15446625"))
    assert not result.eligible
    assert "placeholder_title" in result.reasons


def test_valid_tourist_place_eligible_new() -> None:
    city = City(
        slug="zelenogradsk",
        name="Z",
        country="RU",
        timezone="Europe/Kaliningrad",
        is_active=True,
        launch_status="published",
    )
    result = evaluate_place_route_eligibility(_place(category="museum"), city=city)
    assert result.eligible
    assert result.reasons == ()


def test_is_route_forbidden_category_helper_new() -> None:
    assert is_route_forbidden_category("bus_stop")
    assert not is_route_forbidden_category("museum")


def test_apply_route_eligible_filters_excludes_pharmacy_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="elig-filter-city")
    place_factory(slug="cafe-ok", category="cafe", city_id=city.id)
    place_factory(slug="pharm-x", category="pharmacy", city_id=city.id)
    query = apply_route_eligible_filters(db_session.query(Place).filter(Place.city_id == city.id))
    categories = {row.category for row in query.all()}
    assert "pharmacy" not in categories
    assert "cafe" in categories


@allure.story("Placeholder names are filtered from route candidate SQL")
@allure.severity("critical")
def test_apply_route_eligible_filters_excludes_placeholder_titles_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="elig-placeholder-city")
    place_factory(slug="real-museum", title="Краеведческий музей", category="museum", city_id=city.id)
    place_factory(slug="osm-culture", title="Культурное место OSM 15446625", category="culture", city_id=city.id)

    query = apply_route_eligible_filters(db_session.query(Place).filter(Place.city_id == city.id))
    titles = {row.title for row in query.all()}

    assert "Краеведческий музей" in titles
    assert "Культурное место OSM 15446625" not in titles