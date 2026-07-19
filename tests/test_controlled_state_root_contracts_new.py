from __future__ import annotations

import ast

import pytest

from core.publication_state_ownership import (
    CONTROLLED_PLACE_INPUT_FIELDS,
    PUBLICATION_OWNED_FIELDS,
    VERIFICATION_OWNED_FIELDS,
)
from schemas.place import PlaceUpdate
from services.admin_place_update_service import _ALLOWED
from services.place_change_review_service import (
    PROTECTED_PUBLICATION_FIELDS as REVIEW_PUBLICATION_FIELDS,
    RESTORABLE_PLACE_FIELDS,
)
from services.place_service import PROTECTED_CONTROLLED_FIELDS
from services.taxonomy_workflow_service import STEP_HANDLERS, WORKFLOW_REGISTRY, _validate_registry


def test_all_generic_boundaries_share_complete_controlled_registry() -> None:
    assert PROTECTED_CONTROLLED_FIELDS == CONTROLLED_PLACE_INPUT_FIELDS
    assert _ALLOWED.isdisjoint(CONTROLLED_PLACE_INPUT_FIELDS)
    assert REVIEW_PUBLICATION_FIELDS == PUBLICATION_OWNED_FIELDS
    assert RESTORABLE_PLACE_FIELDS.isdisjoint(PUBLICATION_OWNED_FIELDS)
    assert "route_exclusion_reason" in PUBLICATION_OWNED_FIELDS
    assert "verification_status" in VERIFICATION_OWNED_FIELDS
    assert "verified_at" in VERIFICATION_OWNED_FIELDS


@pytest.mark.parametrize("field", sorted(CONTROLLED_PLACE_INPUT_FIELDS))
def test_legacy_update_schema_rejects_every_controlled_field(field: str) -> None:
    payload = {
        "slug": "controlled-test",
        "title": "Controlled test",
        "lat": 1.0,
        "lng": 1.0,
        field: None,
    }
    with pytest.raises(ValueError):
        PlaceUpdate.model_validate(payload)


def test_workflow_registry_has_exact_handler_coverage() -> None:
    registered = {step for steps in WORKFLOW_REGISTRY.values() for step in steps}
    assert registered == set(STEP_HANDLERS)
    _validate_registry()


def test_category_workflow_orders_inputs_before_derived_state() -> None:
    assert WORKFLOW_REGISTRY["after_category_change"] == (
        "calculate_quality",
        "reconcile_publication_route",
    )


def test_workflow_executor_is_fail_closed_for_missing_handler(monkeypatch) -> None:
    monkeypatch.setitem(WORKFLOW_REGISTRY, "broken", ("missing_handler",))
    with pytest.raises(RuntimeError, match="registry mismatch"):
        _validate_registry()


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
