"""Architecture guard: privileged write routes require admin_required."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi.routing import APIRoute

from core.admin_auth import admin_required
from main import app

# Surfaces hardened in this remediation pass (must stay admin-gated).
_REMEDIATION_PREFIXES = (
    "/v1/verification",
    "/verification",
    "/place-seed",
    "/city-expansion",
)

_WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def _iter_api_routes() -> Iterator[APIRoute]:
    for route in app.routes:
        if isinstance(route, APIRoute):
            yield route


def _depends_on(dependant, target) -> bool:
    if dependant.call is target:
        return True
    return any(_depends_on(child, target) for child in dependant.dependencies)


def test_privileged_write_paths_require_admin_new() -> None:
    missing: list[str] = []
    for route in _iter_api_routes():
        path = route.path
        if not any(path == p or path.startswith(p + "/") for p in _REMEDIATION_PREFIXES):
            continue
        if not _depends_on(route.dependant, admin_required):
            methods = sorted(set(route.methods or ()))
            missing.append(f"{methods}:{path}")
    assert not missing, "admin_required missing on: " + ", ".join(missing)


def test_places_public_mutations_removed_new() -> None:
    """Removed public Place CRUD must stay gone (nested review/suggestion POSTs ok)."""
    forbidden = {
        ("POST", "/places/"),
        ("POST", "/places"),
        ("PUT", "/places/{place_id}"),
        ("DELETE", "/places/{place_id}"),
    }
    found: list[str] = []
    for route in _iter_api_routes():
        for method in set(route.methods or ()) & _WRITE_METHODS:
            if (method, route.path) in forbidden:
                found.append(f"{method}:{route.path}")
    assert found == [], found
