from __future__ import annotations

from uuid import uuid4

from sqlalchemy import update
from sqlalchemy.orm import Session

from models.taxonomy import WorkflowOperation
from services import taxonomy_workflow_service as workflow_service


def _install_probe(monkeypatch) -> None:
    monkeypatch.setitem(workflow_service.WORKFLOW_REGISTRY, "retry_probe", ("probe",))
    monkeypatch.setitem(workflow_service.STEP_HANDLERS, "probe", lambda _db, _operation: None)


def _failed_operation(db_session, *, key: str) -> WorkflowOperation:
    operation = WorkflowOperation(
        id=uuid4().hex,
        workflow="retry_probe",
        request_id=uuid4().hex,
        idempotency_key=f"retry_probe:{key}",
        entity_type="probe",
        entity_id=None,
        payload={},
        actor="test",
        status="failed",
        steps=[{"name": "probe", "status": "pending"}],
        retry_count=0,
        max_retries=3,
        error_message="initial failure",
    )
    db_session.add(operation)
    db_session.commit()
    return operation


def test_retry_uses_fresh_locked_operation_state(db_session, monkeypatch) -> None:
    _install_probe(monkeypatch)
    operation = _failed_operation(db_session, key=uuid4().hex)

    # Materialize stale state in Session A, then update the row through Session B.
    assert operation.status == "failed"
    other = Session(bind=db_session.get_bind(), expire_on_commit=False)
    try:
        other.execute(
            update(WorkflowOperation)
            .where(WorkflowOperation.id == operation.id)
            .values(status="completed", retry_count=1, error_message=None)
        )
        other.commit()
    finally:
        other.close()

    result = workflow_service.retry_workflow(db_session, operation)

    assert result.status == "completed"
    assert result.retry_count == 1
    assert result.error_message is None


def test_completed_workflow_cannot_be_retried_twice(db_session, monkeypatch) -> None:
    _install_probe(monkeypatch)
    operation = _failed_operation(db_session, key=uuid4().hex)

    first = workflow_service.retry_workflow(db_session, operation)
    second = workflow_service.retry_workflow(db_session, first)

    assert first.status == "completed"
    assert second.status == "completed"
    assert first.retry_count == 1
    assert second.retry_count == 1


def test_run_workflow_returns_existing_idempotent_operation(db_session, monkeypatch) -> None:
    _install_probe(monkeypatch)
    key = uuid4().hex

    first = workflow_service.run_workflow(
        db_session,
        workflow="retry_probe",
        request_id=uuid4().hex,
        idempotency_key=key,
        entity_type="probe",
        entity_id=None,
        payload={"attempt": 1},
        actor="test",
    )
    second = workflow_service.run_workflow(
        db_session,
        workflow="retry_probe",
        request_id=uuid4().hex,
        idempotency_key=key,
        entity_type="probe",
        entity_id=None,
        payload={"attempt": 2},
        actor="test",
    )

    assert second.id == first.id
    assert db_session.query(WorkflowOperation).filter(
        WorkflowOperation.idempotency_key == f"retry_probe:{key}"
    ).count() == 1
