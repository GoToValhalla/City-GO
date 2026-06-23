from fastapi.routing import APIRoute

from core.admin_auth import admin_required
from main import app


def test_import_pipeline_admin_routes_require_admin_dependency_new() -> None:
    expected = {
        "/admin/place-enrichment/pipeline/{city_slug}/run",
        "/admin/place-enrichment/jobs/{job_id}/steps",
        "/admin/place-enrichment/places/{place_id}/confidence",
        "/admin/place-enrichment/review-queue",
        "/admin/place-enrichment/review-queue/{item_id}/resolve",
        "/admin/place-enrichment/photo-candidates/{candidate_id}/approve",
        "/admin/place-enrichment/photo-candidates/{candidate_id}/reject",
        "/admin/place-enrichment/photo-candidates/{candidate_id}/set-primary",
    }
    routes = [route for route in app.routes if isinstance(route, APIRoute) and route.path in expected]

    assert {route.path for route in routes} == expected
    assert all(any(dep.call is admin_required for dep in route.dependant.dependencies) for route in routes)
