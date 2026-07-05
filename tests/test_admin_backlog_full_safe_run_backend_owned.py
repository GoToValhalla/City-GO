from __future__ import annotations

from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from models.admin_operation import AdminOperation
from schemas.admin_backlog_reduction import BacklogReductionResult
from services.admin_backlog_full_run_state import SAFE_QUEUE_ACTIONS, create_full_run, mark_stop_requested, read_full_run
import services.admin_backlog_full_run_runner as runner_module


FORBIDDEN_ACTIONS = {
    "recompute_route_eligibility",
    "exclude_service_places_from_routes",
    "classify_unknown_categories_deterministic",
    "normalize_manual_review_backlog",
    "recompute_low_confidence",
}


def _fake_result(action_code: str) -> BacklogReductionResult:
    return BacklogReductionResult(
        action_code=action_code,
        status="applied",
        dry_run=False,
        affected_count=1,
        changed_count=0,
        skipped_count=0,
        failed_count=0,
        queued_count=1,
        limit=500,
        message=f"{action_code} queued",
    )


def test_full_safe_run_start_is_backend_owned_and_uses_only_safe_actions_new(client: TestClient, db_session, monkeypatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(runner_module, "SessionLocal", lambda: db_session)

    def fake_apply(db, request, *, actor: str):
        calls.append(request.action_code)
        return _fake_result(request.action_code)

    monkeypatch.setattr(runner_module, "apply_backlog_reduction", fake_apply)

    response = client.post("/admin/overview/backlog-reduction/full-safe-run/start")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["job_id"]
    assert calls == list(SAFE_QUEUE_ACTIONS)
    assert not (set(calls) & FORBIDDEN_ACTIONS)

    saved = read_full_run(db_session, payload["job_id"])
    assert saved is not None
    assert saved["status"] == "completed"
    assert saved["queued_count"] == 4
    assert saved["remaining_count"] == 0


def test_full_safe_run_stop_requested_prevents_next_actions_new(db_session, monkeypatch) -> None:
    calls: list[str] = []
    created = create_full_run(db_session, actor="admin")
    job_id = int(created["job_id"])
    mark_stop_requested(db_session, job_id, actor="admin")
    monkeypatch.setattr(runner_module, "SessionLocal", lambda: db_session)

    def fake_apply(db, request, *, actor: str):
        calls.append(request.action_code)
        return _fake_result(request.action_code)

    monkeypatch.setattr(runner_module, "apply_backlog_reduction", fake_apply)

    runner_module.run_full_safe_backlog_reduction(job_id, actor="admin")

    saved = read_full_run(db_session, job_id)
    assert saved is not None
    assert calls == []
    assert saved["status"] == "stopped"
    assert saved["stop_requested"] is True


def test_full_safe_run_stale_status_is_lightweight_new(db_session) -> None:
    created = create_full_run(db_session, actor="admin")
    job_id = int(created["job_id"])
    operation = db_session.query(AdminOperation).filter(AdminOperation.id == job_id).one()
    result = dict(operation.result or {})
    result["last_heartbeat_at"] = (datetime.utcnow() - timedelta(minutes=11)).isoformat()
    operation.result = result
    operation.status = "running"
    db_session.commit()

    saved = read_full_run(db_session, job_id)

    assert saved is not None
    assert saved["runtime_status"] == "stuck"
    assert saved["is_stale"] is True
