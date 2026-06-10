"""Тесты route eligibility."""

from __future__ import annotations

from models.city import City
from models.place import Place
from services.route_eligibility import (
    apply_route_eligible_filters,
    evaluate_place_route_eligibility,
    is_route_forbidden_category,
)


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
