from telegram_bot.services.route_payload import (
    first_route_place_id,
    route_place_ids,
    shortened_time_budget,
)


def test_route_place_ids_extracts_ordered_ids() -> None:
    route = {"points": [{"place_id": "1"}, {"place_id": 2}, {"bad": "x"}]}
    assert route_place_ids(route) == ["1", "2"]


def test_first_route_place_id_returns_none_for_empty_route() -> None:
    assert first_route_place_id({"points": []}) is None


def test_shortened_time_budget_uses_context_with_floor() -> None:
    route = {"context": {"time_budget_minutes": 45}}
    assert shortened_time_budget(route) == 30
