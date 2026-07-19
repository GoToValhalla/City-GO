from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from core.publication_state_ownership import CONTROLLED_PLACE_INPUT_FIELDS, VERIFICATION_OWNED_FIELDS
from schemas.admin import AdminPlaceCreate
from schemas.place import PlaceCreate, PlaceUpdate
from services.admin_service import verify_place
from services.place_verification_mutation import transition_place_verification


def _base_payload(**overrides):
    payload = {
        "slug": "controlled-schema-place",
        "title": "Controlled schema place",
        "lat": 54.9,
        "lng": 20.4,
    }
    payload.update(overrides)
    return payload


def test_last_verified_at_is_verification_owned() -> None:
    assert "last_verified_at" in VERIFICATION_OWNED_FIELDS
    assert "last_verified_at" in CONTROLLED_PLACE_INPUT_FIELDS
    with pytest.raises(ValueError):
        PlaceUpdate.model_validate(_base_payload(last_verified_at=datetime.utcnow()))


def test_generic_input_json_schema_hides_all_controlled_fields() -> None:
    for schema_type in (PlaceCreate, PlaceUpdate, AdminPlaceCreate):
        properties = schema_type.model_json_schema().get("properties", {})
        assert set(properties).isdisjoint(CONTROLLED_PLACE_INPUT_FIELDS)


def test_needs_recheck_preserves_last_completed_verification(
    db_session,
    draft_place_factory,
) -> None:
    place = draft_place_factory(slug="needs-recheck-preserves-history")
    previous_verified_at = datetime.utcnow() - timedelta(days=31)
    previous_last_verified_at = previous_verified_at
    place.verification_status = "verified"
    place.verified_by = "previous-verifier"
    place.verified_at = previous_verified_at
    place.last_verified_at = previous_last_verified_at
    place.existence_confidence_score = 95
    place.existence_confidence_level = "high"
    db_session.commit()

    transition_place_verification(
        db_session,
        place,
        to_status="needs_recheck",
        actor="scheduler",
        reason="stale data",
    )
    db_session.commit()
    db_session.refresh(place)

    assert place.verification_status == "needs_recheck"
    assert place.needs_recheck_at is not None
    assert place.verified_by == "previous-verifier"
    assert place.verified_at == previous_verified_at
    assert place.last_verified_at == previous_last_verified_at


def test_single_admin_verify_uses_writer_lock(
    db_session,
    draft_place_factory,
    monkeypatch,
) -> None:
    place = draft_place_factory(slug="single-admin-verify-lock")
    observed = {"for_update": False}
    original = db_session.query

    class QueryProxy:
        def __init__(self, query):
            self._query = query

        def __getattr__(self, name):
            value = getattr(self._query, name)
            if name == "with_for_update":
                def wrapped(*args, **kwargs):
                    observed["for_update"] = True
                    return QueryProxy(value(*args, **kwargs))
                return wrapped
            if callable(value):
                def wrapped(*args, **kwargs):
                    result = value(*args, **kwargs)
                    return QueryProxy(result) if hasattr(result, "filter") else result
                return wrapped
            return value

    monkeypatch.setattr(db_session, "query", lambda *args, **kwargs: QueryProxy(original(*args, **kwargs)))
    result = verify_place(db_session, place.id, actor="test-admin")
    assert result is not None
    assert observed["for_update"] is True
