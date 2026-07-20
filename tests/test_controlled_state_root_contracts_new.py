from __future__ import annotations

import ast
from uuid import uuid4

import pytest

from core.publication_state_ownership import (
    CONTROLLED_PLACE_INPUT_FIELDS,
    PUBLICATION_CONTROLLED_INPUT_FIELDS,
    VERIFICATION_OWNED_FIELDS,
)
from schemas.admin import AdminPlaceUpdate
from schemas.place import PlaceUpdate
from services.admin_place_update_service import _ALLOWED
from services.place_change_review_service import RESTORABLE_PLACE_FIELDS
from services.place_service import PROTECTED_CONTROLLED_FIELDS
from services.taxonomy_workflow_service import (
    STEP_HANDLERS,
    WORKFLOW_REGISTRY,
    _validate_registry,
    run_workflow,
)


def test_all_generic_boundaries_share_complete_controlled_registry() -> None:
    assert PROTECTED_CONTROLLED_FIELDS == CONTROLLED_PLACE_INPUT_FIELDS
    assert _ALLOWED.isdisjoint(CONTROLLED_PLACE_INPUT_FIELDS)
    assert RESTORABLE_PLACE_FIELDS.isdisjoint(CONTROLLED_PLACE_INPUT_FIELDS)
    assert "route_exclusion_reason" in PUBLICATION_CONTROLLED_INPUT_FIELDS
    assert "verification_status" in VERIFICATION_OWNED_FIELDS
    assert "verified_at" in VERIFICATION_OWNED_FIELDS


_VERIFICATION_CONTROLLED_FIELDS = CONTROLLED_PLACE_INPUT_FIELDS - PUBLICATION_CONTROLLED_INPUT_FIELDS


@pytest.mark.parametrize("field", sorted(_VERIFICATION_CONTROLLED_FIELDS))
def test_legacy_update_schema_rejects_verification_controlled_field(field: str) -> None:
    payload = {
        "slug": "controlled-test",
        "title": "Controlled test",
        "lat": 1.0,
        "lng": 1.0,
        field: None,
    }
    with pytest.raises(ValueError):
        PlaceUpdate.model_validate(payload)


@pytest.mark.parametrize("field", sorted(PUBLICATION_CONTROLLED_INPUT_FIELDS))
def test_admin_update_schema_rejects_publication_controlled_field(field: str) -> None:
    payload = {
        "slug": "controlled-test",
        "title": "Controlled test",
        "lat": 1.0,
        "lng": 1.0,
        field: None,
    }
    with pytest.raises(ValueError):
        AdminPlaceUpdate.model_validate(payload)


def test_workflow_registry_has_exact_handler_coverage() -> None:
    registered = {step for steps in WORKFLOW_REGISTRY.values() for step in steps}
    assert registered == set(STEP_HANDLERS)
    _validate_registry()


def test_every_derived_state_workflow_validates_before_reconciliation() -> None:
    for workflow in (
        "after_import",
        "after_place_confirmation",
        "after_photo_confirmation",
        "after_category_change",
        "after_place_update",
    ):
        steps = WORKFLOW_REGISTRY[workflow]
        assert "validate_data" in steps
        assert "reconcile_publication_route" in steps
        assert steps.index("validate_data") < steps.index("reconcile_publication_route")


def test_workflow_executor_is_fail_closed_for_missing_handler(monkeypatch) -> None:
    monkeypatch.setitem(WORKFLOW_REGISTRY, "broken", ("missing_handler",))
    with pytest.raises(RuntimeError, match="registry mismatch"):
        _validate_registry()


def test_failed_workflow_rolls_back_completed_business_steps(
    db_session,
    draft_place_factory,
    monkeypatch,
) -> None:
    place = draft_place_factory(slug="workflow-real-savepoint", title="Original")

    def mutate_title(db, operation) -> None:
        target = db.get(type(place), place.id)
        target.title = "Mutated inside workflow"
        db.flush()

    def fail_second_step(_db, _operation) -> None:
        raise RuntimeError("second step failed")

    monkeypatch.setitem(WORKFLOW_REGISTRY, "rollback_probe", ("probe_mutate", "probe_fail"))
    monkeypatch.setitem(STEP_HANDLERS, "probe_mutate", mutate_title)
    monkeypatch.setitem(STEP_HANDLERS, "probe_fail", fail_second_step)

    operation = run_workflow(
        db_session,
        workflow="rollback_probe",
        request_id=uuid4().hex,
        idempotency_key=uuid4().hex,
        entity_type="place",
        entity_id=str(place.id),
        payload={},
        actor="test",
        commit=False,
    )

    db_session.refresh(place)
    assert operation.status == "failed"
    assert operation.error_message == "second step failed"
    assert place.title == "Original"
    assert all(step["status"] == "pending" for step in operation.steps)


def test_place_aware_guard_example_does_not_confuse_category_fields() -> None:
    tree = ast.parse(
        """
def mutate(place: Place, category: Category):
    place.is_route_eligible = False
    category.is_route_eligible = False
"""
    )
    assignments = [node for node in ast.walk(tree) if isinstance(node, ast.Assign)]
    assert len(assignments) == 2
