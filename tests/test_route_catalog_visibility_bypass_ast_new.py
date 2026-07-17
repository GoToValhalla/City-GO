"""Repository-level regression: no route-context module may query Place
rows through the catalog-only visibility gate (apply_public_place_visibility
/ public_place_conditions), because that gate never checks
Place.is_route_eligible.

Found by independent review: services/user_route_edit_service.py,
services/user_route_place_loader.py, services/user_route_slot_build_service.py,
and services/user_route_replacement_loader.py all used
apply_public_place_visibility to select places later inserted into a live
user route (add_place, replace_place, alternatives, structured_options,
slot-mode build, and the /correct extend_route/remove_place actions) — a
place explicitly marked is_route_eligible=False (e.g. emergency-hidden, or
rejected by admin quality review) could still be publicly catalog-visible
and pass that gate, directly violating the project rule "routes must not
include ... unless explicitly route_eligible".

The correct gate for anything that selects a Place to appear IN a route is
services.route_eligibility.apply_route_eligible_filters (backed by
compile_route_eligible_sql_conditions, the single source of truth in
services/route_eligibility_policy.py), or, for read-only counts/diagnostics
that never return/insert a place (e.g. services/route_candidate_diagnostics.py
comparing places_public_catalog vs places_route_eligible counts side by
side), a bare reference to public_place_conditions()/admin_preview_place_
conditions() without ever being passed to apply_public_place_visibility(...)
is tolerated — this scan only forbids the query-applying WRAPPER call, not
the underlying conditions tuple, since a raw count comparison cannot itself
insert an ineligible place into a route.

This is a source-text AST scan: it discovers every route-context module by
filename pattern (not a fixed list), so it also covers any route module
added after this test was written — the discovery pattern is exactly what
inventoried the 4 bypass files above, plus dozens of legitimate route
modules that don't touch Place visibility at all (this scan is a no-op for
those, since the forbidden call simply doesn't appear).
"""

from __future__ import annotations

import ast
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Forbidden: the catalog-only query-applying wrapper. Never checks
# is_route_eligible. Route-context modules must use
# services.route_eligibility.apply_route_eligible_filters instead (or the
# stricter admin/route variants re-exported from the same package).
FORBIDDEN_CALL = "apply_public_place_visibility"


def _discover_route_context_files() -> tuple[str, ...]:
    """Same discovery rule used to inventory the original 4 bypass files:
    any services/ module named route_*.py or user_route_*.py (including
    package subdirectories whose own directory name contains "route"), plus
    any routers/ module with "route" or "itinerary" in its filename."""
    found: list[str] = []
    for base in ("services", "routers"):
        base_path = REPO_ROOT / base
        for root, _dirs, names in os.walk(base_path):
            rel_root = Path(root).relative_to(REPO_ROOT)
            for name in names:
                if not name.endswith(".py"):
                    continue
                if base == "services":
                    is_route_module = (
                        name.startswith("route_")
                        or name.startswith("user_route_")
                        or "route" in Path(root).name.lower()
                    )
                else:
                    is_route_module = "route" in name.lower() or "itinerary" in name.lower()
                if is_route_module:
                    found.append(str(rel_root / name))
    return tuple(sorted(found))


def _source(path: str) -> str:
    full = REPO_ROOT / path
    return full.read_text(encoding="utf-8")


def _forbidden_call_usages(source: str, path: str) -> list[str]:
    tree = ast.parse(source, filename=path)
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else (func.attr if isinstance(func, ast.Attribute) else None)
            if name == FORBIDDEN_CALL:
                violations.append(f"{path}:{node.lineno}: calls {FORBIDDEN_CALL}() — use apply_route_eligible_filters() instead")
    return violations


def test_route_modules_discovered_and_nonempty_new():
    """Sanity check on the discovery mechanism itself: if this returns an
    empty/tiny list, the glob pattern broke and the main test below would
    silently pass without scanning anything."""
    files = _discover_route_context_files()
    assert len(files) > 50, f"expected many route-context modules, found {len(files)}: {files}"
    assert "services/user_route_edit_service.py" in files
    assert "services/user_route_place_loader.py" in files
    assert "services/user_route_slot_build_service.py" in files
    assert "services/user_route_replacement_loader.py" in files
    assert "routers/user_routes.py" in files


def test_no_catalog_only_visibility_in_route_context_modules_new():
    all_violations: list[str] = []
    for path in _discover_route_context_files():
        source = _source(path)
        all_violations.extend(_forbidden_call_usages(source, path))
    assert not all_violations, (
        "Catalog-only apply_public_place_visibility() found in route-context "
        "module(s) — this gate never checks Place.is_route_eligible, so a "
        "place explicitly excluded from routes could still be inserted "
        "into one:\n" + "\n".join(all_violations)
    )
