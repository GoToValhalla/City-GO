from __future__ import annotations

from fastapi.testclient import TestClient

from models.admin_audit_log import AdminAuditLog
from models.admin_operation import AdminOperation
from models.place import Place
from tests.test_admin_backlog_breakdown_new import _make_place


def _post(client: TestClient, path: str, body: dict[str, object]):
    response = client.post(path, json=body)
    assert response.status_code == 200, response.text
    return response.json()


def test_dry_run_does_not_mutate_places_new(client: TestClient, db_session, place_factory) -> None:
    place = _make_place(db_session, place_factory, "dry-bank", category="bank", canonical_category="bank")
    payload = _post(client, "/admin/overview/backlog-reduction/dry-run", {"action_code": "exclude_service_places_from_routes", "limit": 10})

    db_session.refresh(place)
    assert payload["dry_run"] is True
    assert payload["affected_count"] == 1
    assert payload["changed_count"] == 1
    assert place.is_route_eligible is True
    assert db_session.query(AdminOperation).count() == 0


def test_apply_requires_confirmation_and_keeps_data_new(client: TestClient, db_session, place_factory) -> None:
    place = _make_place(db_session, place_factory, "confirm-bank", category="bank", canonical_category="bank")
    response = client.post("/admin/overview/backlog-reduction/apply", json={"action_code": "exclude_service_places_from_routes", "limit": 10, "confirmation_text": "YES"})

    db_session.refresh(place)
    assert response.status_code == 409
    assert place.is_route_eligible is True
    assert db_session.query(AdminOperation).count() == 0


def test_apply_respects_limit_and_is_idempotent_new(client: TestClient, db_session, place_factory) -> None:
    places = [_make_place(db_session, place_factory, f"limit-bank-{idx}", category="bank", canonical_category="bank") for idx in range(3)]

    first = _post(client, "/admin/overview/backlog-reduction/apply", {"action_code": "exclude_service_places_from_routes", "limit": 2, "confirmation_text": "APPLY"})
    second = _post(client, "/admin/overview/backlog-reduction/apply", {"action_code": "exclude_service_places_from_routes", "limit": 2, "confirmation_text": "APPLY"})

    for place in places:
        db_session.refresh(place)
    assert first["changed_count"] == 2
    assert second["changed_count"] == 1
    assert sum(int(place.is_route_eligible is False) for place in places) == 3


def test_apply_records_job_and_audit_without_deleting_or_unpublishing_new(client: TestClient, db_session, place_factory) -> None:
    place = _make_place(db_session, place_factory, "audit-pharmacy", category="pharmacy", canonical_category="pharmacy")
    payload = _post(client, "/admin/overview/backlog-reduction/apply", {"action_code": "exclude_service_places_from_routes", "limit": 10, "confirmation_text": "APPLY"})

    stored = db_session.get(Place, place.id)
    assert stored is not None
    assert stored.is_published is True
    assert stored.is_visible_in_catalog is True
    assert stored.is_route_eligible is False
    assert payload["job_id"] is not None
    assert payload["audit_id"] is not None
    assert db_session.query(AdminOperation).filter(AdminOperation.operation_type == "backlog_reduction").count() == 1
    assert db_session.query(AdminAuditLog).filter(AdminAuditLog.action == "backlog_reduction_apply").count() == 1


def test_job_endpoint_returns_apply_result_new(client: TestClient, db_session, place_factory) -> None:
    _make_place(db_session, place_factory, "job-bank", category="bank", canonical_category="bank")
    applied = _post(client, "/admin/overview/backlog-reduction/apply", {"action_code": "exclude_service_places_from_routes", "limit": 10, "confirmation_text": "APPLY"})

    response = client.get(f"/admin/overview/backlog-reduction/jobs/{applied['job_id']}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["action_code"] == "exclude_service_places_from_routes"
    assert payload["changed_count"] == 1
