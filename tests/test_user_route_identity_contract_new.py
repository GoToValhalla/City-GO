from __future__ import annotations

import pytest

from core.config import settings
from schemas.user_route import UserRouteIntent, UserRoutePoint, UserRouteState
from services.public_route_place_access import resolve_route_scope
from services.user_route_state_integrity import (
    UserRouteStateIntegrityError,
    sign_user_route_state,
    verify_user_route_state,
)


def _point(place_id: str, *, city_slug: str = "identity-city", position: int = 1) -> UserRoutePoint:
    return UserRoutePoint(
        place_id=place_id,
        city_slug=city_slug,
        position=position,
        lat=54.96,
        lng=20.47,
        category="museum",
        visit_minutes=20,
    )


def _route(place_ids: list[str], *, city_slug: str = "identity-city") -> UserRouteState:
    return UserRouteState(
        route_id="identity-route",
        revision=1,
        context=UserRouteIntent(lat=54.96, lng=20.47, city_id=city_slug, time_budget_minutes=120),
        total_places=len(place_ids),
        total_minutes=20 * len(place_ids),
        total_estimated_minutes=20 * len(place_ids),
        estimated_distance=0.0,
        has_warnings=False,
        warning_count=0,
        points=[_point(place_id, city_slug=city_slug, position=index) for index, place_id in enumerate(place_ids, 1)],
    )


def test_signed_route_rejects_city_and_place_tampering_new(monkeypatch) -> None:
    monkeypatch.setattr(settings, "user_route_state_secret", "test-route-secret")
    signed = sign_user_route_state(_route(["1", "2"]))
    verify_user_route_state(signed)

    with pytest.raises(UserRouteStateIntegrityError):
        verify_user_route_state(signed.model_copy(update={"context": signed.context.model_copy(update={"city_id": "other-city"})}))

    with pytest.raises(UserRouteStateIntegrityError):
        verify_user_route_state(signed.model_copy(update={"points": [_point("1"), _point("3", position=2)]}))


def test_signed_route_rejects_route_id_and_revision_tampering_new(monkeypatch) -> None:
    monkeypatch.setattr(settings, "user_route_state_secret", "test-route-secret")
    signed = sign_user_route_state(_route(["1"]))
    with pytest.raises(UserRouteStateIntegrityError):
        verify_user_route_state(signed.model_copy(update={"route_id": "other-route"}))
    with pytest.raises(UserRouteStateIntegrityError):
        verify_user_route_state(signed.model_copy(update={"revision": 2}))


def test_production_rejects_unsigned_route_state_new(monkeypatch) -> None:
    monkeypatch.setattr(settings, "app_env", "production")
    monkeypatch.setattr(settings, "user_route_state_secret", "test-route-secret")
    with pytest.raises(UserRouteStateIntegrityError):
        verify_user_route_state(_route(["1"]))


def test_route_scope_rejects_context_city_mismatch_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="identity-city")
    other = city_factory(slug="identity-other")
    place = place_factory(city_id=city.id, slug="identity-place", category="museum", lat=54.96, lng=20.47)
    route = _route([str(place.id)], city_slug=other.slug)
    assert resolve_route_scope(db_session, route) is None


def test_route_scope_rejects_invalid_duplicate_and_missing_ids_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="identity-city")
    place = place_factory(city_id=city.id, slug="identity-place-2", category="museum", lat=54.96, lng=20.47)

    assert resolve_route_scope(db_session, _route([str(place.id), "tampered"], city_slug=city.slug)) is None
    assert resolve_route_scope(db_session, _route([str(place.id), str(place.id)], city_slug=city.slug)) is None
    assert resolve_route_scope(db_session, _route([str(place.id), "999999999"], city_slug=city.slug)) is None
