from __future__ import annotations

from pathlib import Path

from architecture.guards import forbidden_dependency_violations, model_imports, transaction_calls


ROOT = Path(__file__).resolve().parents[1]


def _files(patterns: tuple[str, ...]) -> tuple[Path, ...]:
    return tuple(sorted({path for pattern in patterns for path in ROOT.glob(pattern)}))


def test_search_and_routing_do_not_import_each_other() -> None:
    search = _files(("services/search_projection_*.py", "services/place_search_service.py", "routers/place_search.py"))
    routing = _files(("services/routing_projection_*.py", "services/candidate_retrieval_service.py", "services/route_builder_*.py"))

    assert not forbidden_dependency_violations(
        root=ROOT, sources=search, forbidden_prefixes=("services.routing", "services.route_"),
        rule="search_to_routing",
    )
    assert not forbidden_dependency_violations(
        root=ROOT, sources=routing, forbidden_prefixes=("services.search",),
        rule="routing_to_search",
    )


def test_routing_does_not_depend_on_route_sessions() -> None:
    routing = _files(("services/routing_projection_*.py", "services/candidate_retrieval_service.py", "services/route_builder_*.py"))

    assert not forbidden_dependency_violations(
        root=ROOT,
        sources=routing,
        forbidden_prefixes=("services.route_session", "services.user_route_session", "models.route_session"),
        rule="routing_to_route_sessions",
    )


def test_guard_reports_exact_import_location(tmp_path: Path) -> None:
    probe = tmp_path / "routing_probe.py"
    probe.write_text("from services.route_session_service import start_route_session\n")

    violations = forbidden_dependency_violations(
        root=tmp_path,
        sources=(probe,),
        forbidden_prefixes=("services.route_session",),
        rule="routing_to_route_sessions",
    )

    assert [(row.path, row.line, row.rule) for row in violations] == [
        ("routing_probe.py", 1, "routing_to_route_sessions")
    ]


def test_isolated_admin_routers_do_not_import_models_or_own_transactions() -> None:
    names = (
        "admin_taxonomy.py", "admin_destinations.py", "admin_reviews.py",
        "admin_destination_pipeline.py", "admin_route_eligibility.py",
        "route_feedback.py", "admin_projections.py",
    )
    routers = tuple(ROOT / "routers" / name for name in names)

    assert {path.name: model_imports(path) for path in routers} == {
        name: () for name in names
    }
    assert {path.name: transaction_calls(path) for path in routers} == {
        name: () for name in names
    }


def test_non_destination_readers_use_membership_contract() -> None:
    readers = _files((
        "services/search_projection_*.py", "services/catalog_projection_read_service.py",
        "services/candidate_retrieval_service.py", "services/admin_places_filters.py",
    ))

    assert not forbidden_dependency_violations(
        root=ROOT, sources=readers,
        forbidden_prefixes=("models.destination", "services.destination_membership_service"),
        rule="destination_membership_contract",
    )
