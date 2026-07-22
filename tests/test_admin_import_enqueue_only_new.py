"""F04 regression: admin import endpoints must enqueue work and never
execute it. Only the dedicated import worker (data/scripts/
run_admin_import_worker.py, via services.admin_city_import_tasks.
run_queued_import_jobs) may claim and run a CityAdminImportJob.

Before this fix, POST /admin/cities/import additionally dispatched
background_tasks.add_task(run_import_job_background, ...) — a FastAPI
BackgroundTasks callback that claimed and ran the full import pipeline
synchronously inside the API server process, bypassing the worker's
memory/runtime limits, lifecycle, ownership, observability, and recovery
guarantees. run_import_job_background and its two never-called siblings
(run_enrichment_job_background, run_all_cities_enrichment_background) were
deleted; the endpoint now only enqueues via create_city_and_queue_import.
"""

from __future__ import annotations

import inspect

import routers.admin as admin_router
import services.admin_city_import_tasks as tasks_module
from models.city_admin_import_job import CityAdminImportJob


def test_admin_router_no_longer_imports_background_task_dispatch_new() -> None:
    """The router module must not reference the deleted background-execution
    function at all — not importable, not monkeypatchable back in."""
    assert not hasattr(admin_router, "run_import_job_background")
    assert not hasattr(admin_router, "BackgroundTasks")


def test_deleted_background_execution_functions_do_not_exist_new() -> None:
    for name in (
        "run_import_job_background",
        "run_enrichment_job_background",
        "run_all_cities_enrichment_background",
    ):
        assert not hasattr(tasks_module, name), f"{name} must not exist — F04 removed all in-process import execution"


def test_create_city_import_endpoint_has_no_background_tasks_parameter_new() -> None:
    """A FastAPI BackgroundTasks parameter is itself the mechanism this
    task removes — its absence from the endpoint signature is a stronger
    guarantee than mocking it out, since it proves the capability to
    dispatch background work is gone, not merely unused this call."""
    signature = inspect.signature(admin_router.create_city_import)
    annotation_names = {getattr(param.annotation, "__name__", "") for param in signature.parameters.values()}
    assert "BackgroundTasks" not in annotation_names


def test_create_city_import_enqueues_only_and_returns_immediately_new(client, monkeypatch) -> None:
    """The admin mobile/desktop flow: submitting the city-create form must
    still succeed with the same response shape, and the job it creates
    must stay status="queued" — nothing may have claimed or executed it
    as a side effect of the HTTP request completing."""
    calls: list[str] = []
    monkeypatch.setattr(
        "services.admin_city_import_tasks.claim_queued_job",
        lambda *_a, **_k: calls.append("claim_queued_job") or None,
    )
    monkeypatch.setattr(
        "services.admin_city_import_job_service.run_city_import_job",
        lambda *_a, **_k: calls.append("run_city_import_job") or None,
    )

    response = client.post(
        "/admin/cities/import",
        json={
            "name": "Черняховск",
            "country": "Россия",
            "region": "Калининградская область",
            "center_lat": 54.63,
            "center_lng": 21.81,
            "radius_km": 10,
            "actor": "qa",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["job_status"] == "queued"
    assert payload["city_name"] == "Черняховск"
    assert "message" in payload and "next_step" in payload

    # Nothing claimed or ran as a side effect of the HTTP request.
    assert calls == []

    jobs_response = client.get("/admin/import-jobs")
    assert jobs_response.status_code == 200
    items = jobs_response.json().get("items") or []
    matching = [item for item in items if item.get("city_name") == "Черняховск"]
    assert matching, "the enqueued job must be visible in the admin queue"
    assert matching[0]["status"] == "queued"
    assert matching[0].get("claimed_by") is None


def test_create_city_import_job_remains_queued_in_db_after_request_new(client, db_session) -> None:
    """Direct DB-level proof, independent of the admin list endpoint's own
    serialization: the row this request created is still status="queued",
    claimed_by is NULL, started_at is NULL -- claim_queued_job (the only
    legitimate claim path) was never called for it."""
    response = client.post(
        "/admin/cities/import",
        json={"name": "Гусев", "country": "Россия", "actor": "qa"},
    )
    assert response.status_code == 200
    city_id = response.json()["city_id"]

    job = (
        db_session.query(CityAdminImportJob)
        .filter(CityAdminImportJob.city_id == city_id)
        .order_by(CityAdminImportJob.created_at.desc())
        .first()
    )
    assert job is not None
    assert job.status == "queued"
    assert job.claimed_by is None
    assert job.started_at is None
    assert job.finished_at is None


def test_only_run_queued_import_jobs_can_claim_and_execute_new(client, db_session, monkeypatch) -> None:
    """Simulates what the worker (not the API) is supposed to do next:
    calling run_queued_import_jobs is the only path that claims and runs
    the job the endpoint above created. This proves the worker is not
    merely "also capable" of running it, but the SOLE path exercised in
    this test that ever calls run_city_import_job."""
    ran_with: dict[str, object] = {}

    def fake_run_city_import_job(db, *, city_id, actor_id, job_id):
        ran_with["city_id"] = city_id
        ran_with["job_id"] = job_id
        job = db.query(CityAdminImportJob).filter(CityAdminImportJob.id == job_id).first()
        job.status = "success"
        from datetime import datetime

        job.finished_at = datetime.utcnow()
        db.commit()
        return job

    monkeypatch.setattr(tasks_module, "run_city_import_job", fake_run_city_import_job)
    # run_queued_import_jobs opens its own SessionLocal() internally (the
    # real worker's own pattern) — reuse the test's db_session connection
    # for it, same as tests/test_admin_import_worker_decisions.py's
    # _patch_session_local, so the row the HTTP request just committed is
    # actually visible to it.

    class _SessionContext:
        def __enter__(self):
            return db_session

        def __exit__(self, *_exc):
            return False

    monkeypatch.setattr(tasks_module, "SessionLocal", lambda: _SessionContext())

    response = client.post(
        "/admin/cities/import",
        json={"name": "Советск", "country": "Россия", "actor": "qa"},
    )
    assert response.status_code == 200
    city_id = response.json()["city_id"]

    job_before = (
        db_session.query(CityAdminImportJob)
        .filter(CityAdminImportJob.city_id == city_id)
        .order_by(CityAdminImportJob.created_at.desc())
        .first()
    )
    assert job_before.status == "queued"

    result = tasks_module.run_queued_import_jobs(actor_id="worker-test", limit=1)

    assert result["processed"] == 1
    assert ran_with["city_id"] == city_id
    assert ran_with["job_id"] == job_before.id
