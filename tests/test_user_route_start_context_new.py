from __future__ import annotations

from schemas.user_route import UserRouteBuildRequest


def test_user_route_build_request_new_accepts_start_address() -> None:
    payload = UserRouteBuildRequest(
        lat=0,
        lng=0,
        start_address="Мира 1",
        start_source="address",
        time_budget_minutes=120,
        city_id="khanty-mansiysk",
    )

    assert payload.start_address == "Мира 1"
    assert payload.start_source == "address"
    assert payload.city_id == "khanty-mansiysk"


def test_user_route_build_request_new_accepts_geolocation_source() -> None:
    payload = UserRouteBuildRequest(
        lat=61.0,
        lng=69.0,
        start_source="geolocation",
        time_budget_minutes=120,
        city_id="khanty-mansiysk",
    )

    assert payload.lat == 61.0
    assert payload.lng == 69.0
    assert payload.start_source == "geolocation"
