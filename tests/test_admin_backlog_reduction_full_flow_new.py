from __future__ import annotations

from fastapi.testclient import TestClient

from models.data_foundation import CityEnrichmentRun, EnrichmentTask
from tests.test_admin_backlog_breakdown_new import _make_place


def _apply(client: TestClient, action_code: str, *, limit: int = 10) -> dict[str, object]:
    response = client.post(
        "/admin/overview/backlog-reduction/apply",
        json={"action_code": action_code, "confirmation_text": "APPLY", "limit": limit, "include_samples": True},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_backlog_reduction_apply_enqueues_photo_tasks_new(client: TestClient, db_session, place_factory) -> None:
    place = _make_place(db_session, place_factory, "apply-photo-queue", image_url=None)

    payload = _apply(client, "enqueue_photo_discovery")

    assert payload["status"] == "applied"
    assert payload["queued_count"] == 1
    assert payload["changed_count"] == 0

    task = db_session.query(EnrichmentTask).filter(EnrichmentTask.place_id == place.id).one()
    assert task.task_type == "photo_discovery"
    assert task.status == "queued"
    assert task.city_id == place.city_id
    assert task.payload["action_code"] == "enqueue_photo_discovery"

    run = db_session.query(CityEnrichmentRun).filter(CityEnrichmentRun.id == task.run_id).one()
    assert run.run_type == "backlog_reduction"
    assert run.stage == "enqueue_photo_discovery"
    assert run.progress_total == 1


def test_backlog_reduction_apply_does_not_duplicate_active_tasks_new(client: TestClient, db_session, place_factory) -> None:
    place = _make_place(db_session, place_factory, "apply-photo-dedup", image_url=None)
    db_session.add(EnrichmentTask(city_id=place.city_id, place_id=place.id, task_type="photo_discovery", status="queued"))
    db_session.commit()

    payload = _apply(client, "enqueue_photo_discovery")

    assert payload["queued_count"] == 0
    assert payload["skipped_count"] == 1
    assert payload["skipped_reasons"]["already_queued"] == 1
    assert db_session.query(EnrichmentTask).filter(EnrichmentTask.place_id == place.id, EnrichmentTask.task_type == "photo_discovery").count() == 1


def test_backlog_reduction_apply_classifies_obvious_unknown_category_new(client: TestClient, db_session, place_factory) -> None:
    place = _make_place(db_session, place_factory, "apply-unknown-museum", title="Музей истории", category="unknown", canonical_category="unknown")

    payload = _apply(client, "classify_unknown_categories_deterministic")
    db_session.refresh(place)

    assert payload["changed_count"] == 1
    assert place.canonical_category == "museum"
    assert place.is_route_eligible is True


def test_backlog_reduction_apply_excludes_service_places_from_routes_new(client: TestClient, db_session, place_factory) -> None:
    place = _make_place(db_session, place_factory, "apply-service-bank", category="bank", canonical_category="bank", is_route_eligible=True)

    payload = _apply(client, "exclude_service_places_from_routes")
    db_session.refresh(place)

    assert payload["changed_count"] == 1
    assert place.is_route_eligible is False
    assert place.route_exclusion_reason == "service_category"


def test_backlog_breakdown_exposes_latest_apply_result_new(client: TestClient, db_session, place_factory) -> None:
    _make_place(db_session, place_factory, "apply-latest-result", image_url=None)

    apply_payload = _apply(client, "enqueue_photo_discovery")
    response = client.get("/admin/overview/backlog-breakdown")

    assert response.status_code == 200
    latest = response.json()["last_reduction_result"]
    assert latest["job_id"] == apply_payload["job_id"]
    assert latest["action_code"] == "enqueue_photo_discovery"
    assert latest["queued_count"] == 1
