from schemas.user_route import UserRouteIntent
from services.user_route_context import merge_unique, to_request_context, with_updates


def test_to_request_context_maps_intent() -> None:
    intent = UserRouteIntent(lat=54.96, lng=20.48, interests=["coffee"])
    ctx = to_request_context(intent)
    assert ctx.location == (54.96, 20.48)
    assert ctx.interests == ["coffee"]


def test_with_updates_preserves_and_overrides_values() -> None:
    intent = UserRouteIntent(lat=1.0, lng=2.0, avoided_categories=["bar"])
    updated = with_updates(intent, lat=3.0, avoided_categories=["museum"])
    assert updated.lat == 3.0
    assert updated.lng == 2.0
    assert updated.avoided_categories == ["museum"]


def test_merge_unique_keeps_order() -> None:
    assert merge_unique(["a", "b"], ["b", "c"]) == ["a", "b", "c"]
