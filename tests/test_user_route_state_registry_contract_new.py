from __future__ import annotations

import ast
from pathlib import Path

import pytest

from schemas.user_route import UserRouteIntent, UserRoutePoint, UserRouteState
from services.user_route_state_registry_service import (
    UserRouteStateConflictError,
    advance_route_state,
    register_initial_route_state,
    verify_current_route_state,
)

ROOT = Path(__file__).resolve().parent.parent


def _state(place, city_slug: str, *, route_id: str = "registry-route", revision: int = 1) -> UserRouteState:
    return UserRouteState(
        route_id=route_id,
        revision=revision,
        status="ready",
        context=UserRouteIntent(lat=float(place.lat), lng=float(place.lng), city_id=city_slug, time_budget_minutes=120),
        total_places=1,
        total_minutes=20,
        total_estimated_minutes=20,
        estimated_distance=0.0,
        has_warnings=False,
        warning_count=0,
        points=[
            UserRoutePoint(
                place_id=str(place.id),
                city_slug=city_slug,
                position=1,
                title=place.title,
                address=place.address,
                lat=float(place.lat),
                lng=float(place.lng),
                category=str(place.category or "museum"),
                visit_minutes=20,
            )
        ],
    )


def test_register_initial_state_is_idempotent_for_identical_state_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="registry-idempotent-city")
    place = place_factory(city_id=city.id, slug="registry-idempotent-place", category="museum")
    state = _state(place, city.slug)

    first = register_initial_route_state(db_session, state)
    second = register_initial_route_state(db_session, state)

    assert second.state_token == first.state_token
    assert verify_current_route_state(db_session, first, lock=False).revision == 1


def test_register_initial_state_rejects_same_route_id_with_other_identity_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="registry-conflict-city")
    first_place = place_factory(city_id=city.id, slug="registry-conflict-first", category="museum")
    second_place = place_factory(city_id=city.id, slug="registry-conflict-second", category="park")
    register_initial_route_state(db_session, _state(first_place, city.slug))

    with pytest.raises(UserRouteStateConflictError):
        register_initial_route_state(db_session, _state(second_place, city.slug))


def test_advance_invalidates_previous_revision_even_for_noop_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="registry-noop-city")
    place = place_factory(city_id=city.id, slug="registry-noop-place", category="museum")
    previous = register_initial_route_state(db_session, _state(place, city.slug))
    registry = verify_current_route_state(db_session, previous, lock=True)
    noop = previous.model_copy(update={"warnings": ["No change"], "has_warnings": True, "warning_count": 1})

    issued = advance_route_state(db_session, previous=previous, next_state=noop, registry=registry)

    assert issued.revision == previous.revision + 1
    with pytest.raises(UserRouteStateConflictError):
        verify_current_route_state(db_session, previous, lock=False)
    assert verify_current_route_state(db_session, issued, lock=False).revision == issued.revision


def test_advance_rejects_scope_change_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="registry-scope-a")
    other = city_factory(slug="registry-scope-b")
    place = place_factory(city_id=city.id, slug="registry-scope-place-a", category="museum")
    foreign = place_factory(city_id=other.id, slug="registry-scope-place-b", category="museum")
    previous = register_initial_route_state(db_session, _state(place, city.slug))
    registry = verify_current_route_state(db_session, previous, lock=True)

    with pytest.raises(UserRouteStateConflictError):
        advance_route_state(
            db_session,
            previous=previous,
            next_state=_state(foreign, other.slug, route_id=previous.route_id, revision=2),
            registry=registry,
        )


def test_router_owns_complete_route_state_lifecycle_new() -> None:
    tree = ast.parse((ROOT / "routers/user_routes.py").read_text(encoding="utf-8"))
    calls = {
        node.func.id if isinstance(node.func, ast.Name) else node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, (ast.Name, ast.Attribute))
    }
    assert {"register_initial_route_state", "verify_current_route_state", "advance_route_state"} <= calls


def test_route_services_do_not_commit_or_rollback_request_transactions_new() -> None:
    violations: list[str] = []
    for path in (ROOT / "services").glob("user_route_*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in {"commit", "rollback"}:
                violations.append(f"{path.name}:{node.lineno}:{node.func.attr}")
    assert not violations, "route services must not own request transactions:\n" + "\n".join(violations)


def test_session_transitions_and_registry_verification_use_row_locks_new() -> None:
    session_source = (ROOT / "services/user_route_session_service.py").read_text(encoding="utf-8")
    registry_source = (ROOT / "services/user_route_state_registry_service.py").read_text(encoding="utf-8")
    assert ".with_for_update()" in session_source
    assert ".with_for_update()" in registry_source
    assert "begin_nested" in session_source
