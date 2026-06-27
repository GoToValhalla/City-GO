from fastapi.routing import APIRoute

from core.admin_auth import admin_required
from main import app
from models.data_quality import DataQualityCandidate, DataQualityIssue
from services.city_readiness import compute_city_readiness
from services.data_quality.constants import (
    ISSUE_MISSING_ADDRESS,
    ISSUE_MISSING_PHOTO,
    ISSUE_ROUTE_SUSPICIOUS,
)
from services.data_quality.refresh import refresh_data_quality_issues


def test_missing_photo_issue_created_for_published_place_without_photo_new(db_session, place_factory):
    place = place_factory(address="ул. Морская, 1", is_published=True, image_url=None)
    refresh_data_quality_issues(db_session, city_id=place.city_id)

    issue = _issue(db_session, ISSUE_MISSING_PHOTO)
    assert issue.place_id == place.id
    assert issue.severity == "high"


def test_missing_photo_refresh_is_idempotent_new(db_session, place_factory):
    place = place_factory(address="ул. Морская, 2", image_url=None)
    first = refresh_data_quality_issues(db_session, city_id=place.city_id)
    second = refresh_data_quality_issues(db_session, city_id=place.city_id)

    assert first.created >= 1
    assert second.created == 0
    assert db_session.query(DataQualityIssue).filter_by(issue_type=ISSUE_MISSING_PHOTO).count() == 1


def test_missing_address_issue_created_new(db_session, place_factory):
    place = place_factory(image_url="https://example.test/photo.jpg", address=None)
    refresh_data_quality_issues(db_session, city_id=place.city_id)

    issue = _issue(db_session, ISSUE_MISSING_ADDRESS)
    assert issue.place_id == place.id
    assert issue.reason == "address_missing"


def test_route_eligibility_suspicious_issue_for_stoplist_category_new(db_session, place_factory):
    place = place_factory(category="pharmacy", address="ул. Аптечная, 1", image_url="https://example.test/p.jpg")
    refresh_data_quality_issues(db_session, city_id=place.city_id)

    issue = _issue(db_session, ISSUE_ROUTE_SUSPICIOUS)
    assert issue.place_id == place.id
    assert "pharmacy" in issue.evidence["matched_categories"]


def test_route_eligibility_audit_candidate_does_not_mutate_place_new(client, db_session, place_factory):
    place = place_factory(category="pharmacy", address="ул. Аптечная, 2", image_url="https://example.test/p.jpg")
    refresh_data_quality_issues(db_session, city_id=place.city_id)

    response = client.post("/admin/data-quality/bulk-actions/apply", json={
        "action_type": "propose_exclude_from_routes",
        "filters": {"issue_type": ISSUE_ROUTE_SUSPICIOUS, "status": "open"},
        "confirm": True,
        "reason": "служебная категория для ручной проверки",
    })

    assert response.status_code == 200
    db_session.refresh(place)
    assert place.is_route_eligible is True
    assert db_session.query(DataQualityCandidate).count() == 1


def test_bulk_preview_returns_affected_count_and_sample_new(client, db_session, place_factory):
    place = place_factory(category="bank", address="ул. Банковская, 1", image_url="https://example.test/p.jpg")
    refresh_data_quality_issues(db_session, city_id=place.city_id)

    response = client.post("/admin/data-quality/bulk-actions/preview", json={
        "action_type": "propose_exclude_from_routes",
        "filters": {"issue_type": ISSUE_ROUTE_SUSPICIOUS, "status": "open"},
    })

    payload = response.json()
    assert response.status_code == 200
    assert payload["affected_count"] == 1
    assert payload["sample"][0]["place"]["id"] == place.id


def test_repeated_bulk_apply_does_not_duplicate_candidate_new(client, db_session, place_factory):
    place = place_factory(category="atm", address="ул. Наличная, 1", image_url="https://example.test/p.jpg")
    refresh_data_quality_issues(db_session, city_id=place.city_id)
    body = {
        "action_type": "propose_exclude_from_routes",
        "filters": {"issue_type": ISSUE_ROUTE_SUSPICIOUS},
        "confirm": True,
        "reason": "служебная категория",
    }

    assert client.post("/admin/data-quality/bulk-actions/apply", json=body).status_code == 200
    assert client.post("/admin/data-quality/bulk-actions/apply", json=body).status_code == 200
    assert db_session.query(DataQualityCandidate).count() == 1


def test_diagnostic_gates_do_not_block_publication_when_disabled_new(db_session, place_factory):
    place = place_factory(category="pharmacy", address="ул. Аптечная, 3", image_url="https://example.test/p.jpg")
    refresh_data_quality_issues(db_session, city_id=place.city_id)

    readiness = compute_city_readiness(db_session, city_slug=place.city.slug)
    diagnostics = readiness["data_quality_diagnostics"]
    assert diagnostics["hard_gates_enabled"] is False
    assert diagnostics["blocks_publication"] is False
    assert "route_eligibility_suspicious" in diagnostics["failed_gates"]


def test_summary_counters_match_created_issues_new(client, db_session, place_factory):
    place = place_factory(address=None, image_url=None)
    refresh_data_quality_issues(db_session, city_id=place.city_id)

    payload = client.get("/admin/data-quality/summary").json()
    assert payload["totals"]["published_without_photo"] == 1
    assert payload["totals"]["without_address"] == 1
    assert payload["totals"]["open_issues"] >= 2


def test_data_quality_admin_routes_require_admin_dependency_new():
    expected = {
        "/admin/data-quality/summary",
        "/admin/data-quality/issues",
        "/admin/data-quality/issues/refresh",
        "/admin/data-quality/bulk-actions/preview",
        "/admin/data-quality/bulk-actions/apply",
    }
    routes = [route for route in app.routes if isinstance(route, APIRoute) and route.path in expected]

    assert {route.path for route in routes} == expected
    assert all(any(dep.call is admin_required for dep in route.dependant.dependencies) for route in routes)


def _issue(db_session, issue_type: str) -> DataQualityIssue:
    row = db_session.query(DataQualityIssue).filter_by(issue_type=issue_type).first()
    assert row is not None
    return row
