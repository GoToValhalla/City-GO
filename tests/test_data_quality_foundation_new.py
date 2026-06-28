from fastapi.routing import APIRoute

from core.admin_auth import admin_required
from main import app
from models.data_quality import DataQualityCandidate, DataQualityIssue
from services.city_readiness import compute_city_readiness
from services.data_quality.constants import (
    ISSUE_MISSING_ADDRESS,
    ISSUE_MISSING_PHOTO,
    ISSUE_POSSIBLE_DUPLICATE,
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


def test_refresh_resolves_stale_issue_when_current_state_is_fixed_new(db_session, place_factory):
    place = place_factory(address=None, image_url="https://example.test/photo.jpg")
    refresh_data_quality_issues(db_session, city_id=place.city_id)
    issue = _issue(db_session, ISSUE_MISSING_ADDRESS)
    assert issue.status == "open"

    place.address = "ул. Исправленная, 1"
    db_session.commit()
    second = refresh_data_quality_issues(db_session, city_id=place.city_id)
    db_session.refresh(issue)

    assert second.resolved == 1
    assert issue.status == "resolved"
    assert issue.resolved_at is not None


def test_default_issue_list_hides_resolved_issues_new(client, db_session, place_factory):
    place = place_factory(address=None, image_url="https://example.test/photo.jpg")
    refresh_data_quality_issues(db_session, city_id=place.city_id)
    place.address = "ул. Исправленная, 2"
    db_session.commit()
    refresh_data_quality_issues(db_session, city_id=place.city_id)

    current = client.get(f"/admin/data-quality/issues?issue_type={ISSUE_MISSING_ADDRESS}").json()
    resolved = client.get(f"/admin/data-quality/issues?issue_type={ISSUE_MISSING_ADDRESS}&status=resolved").json()

    assert current["total"] == 0
    assert resolved["total"] == 1


def test_missing_address_issue_created_new(db_session, place_factory):
    place = place_factory(image_url="https://example.test/photo.jpg", address=None)
    refresh_data_quality_issues(db_session, city_id=place.city_id)

    issue = _issue(db_session, ISSUE_MISSING_ADDRESS)
    assert issue.place_id == place.id
    assert issue.reason == "address_missing"


def test_possible_duplicate_issue_created_for_nearby_same_title_new(db_session, city_factory, place_factory):
    city = city_factory(slug="duplicate-city")
    first = place_factory(
        city_id=city.id,
        slug="dostyk-plaza-a",
        title="Dostyk Plaza",
        lat=43.2390,
        lng=76.9450,
        address="Самал-2, 111",
        image_url="https://example.test/dostyk-a.jpg",
    )
    second = place_factory(
        city_id=city.id,
        slug="dostyk-plaza-b",
        title="Dostyk Plaza",
        lat=43.2395,
        lng=76.9455,
        address="Самал-2, 111",
        image_url="https://example.test/dostyk-b.jpg",
    )

    refresh_data_quality_issues(db_session, city_id=city.id)

    issues = db_session.query(DataQualityIssue).filter_by(issue_type=ISSUE_POSSIBLE_DUPLICATE).all()
    assert {issue.place_id for issue in issues} == {first.id, second.id}
    assert all(sorted(issue.evidence["duplicate_place_ids"]) == sorted([first.id, second.id]) for issue in issues)


def test_data_quality_summary_city_score_uses_live_quality_not_stored_readiness_new(
    client, db_session, city_factory, place_factory,
):
    city = city_factory(slug="summary-live-score")
    city.readiness_score = 0
    db_session.add(city)
    place_factory(
        city_id=city.id,
        address=None,
        image_url="https://example.test/photo.jpg",
    )
    refresh_data_quality_issues(db_session, city_id=city.id)

    row = next(item for item in client.get("/admin/data-quality/summary").json()["by_city"] if item["city_slug"] == city.slug)

    assert row["coverage_score"] > 0
    assert row["stored_coverage_score"] == 0
    assert row["primary_blocker"] == "no_address"


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