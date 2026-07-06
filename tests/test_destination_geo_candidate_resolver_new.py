from __future__ import annotations

import pytest

from models.destination import DestinationScope
from services.destination_admin_validation import ValidationIssue
from services.destination_geo_candidate_service import (
    build_destination_payload,
    build_scope_payload,
    candidate_from_input,
    recover_or_create_scope,
    search_destination_geo_candidates,
)
from schemas.destination_geo import DestinationGeoCandidateInput
from tests.destination_pipeline_helpers import destination_with_scope


def _candidate_input(**overrides) -> DestinationGeoCandidateInput:
    base = {
        "candidate_key": "relation:42",
        "title": "Куршская коса",
        "display_name": "Куршская коса, область",
        "lat": 55.17,
        "lng": 20.86,
        "bbox": {"south": 54.94, "west": 20.43, "north": 55.32, "east": 20.99},
        "osm_type": "relation",
        "osm_id": 42,
        "destination_type": "tourist_cluster",
        "import_strategy": "osm_relation",
    }
    base.update(overrides)
    return DestinationGeoCandidateInput(**base)


def test_geo_search_uses_deterministic_adapter_new(monkeypatch):
    monkeypatch.setenv("CITYGO_DESTINATION_GEO_ADAPTER", "deterministic")
    rows = search_destination_geo_candidates("куршская коса", limit=2)
    assert len(rows) == 2
    assert rows[0].import_strategy == "osm_relation"
    assert rows[0].bbox is not None


def test_build_destination_payload_from_candidate_new():
    payload = build_destination_payload(candidate_from_input(_candidate_input()), slug="kursh-kosa", name="Коса")
    assert payload["slug"] == "kursh-kosa"
    assert payload["center_lat"] == 55.17
    assert payload["bbox"]["north"] == 55.32


def test_build_scope_payload_defaults_new():
    payload = build_scope_payload(candidate_from_input(_candidate_input()), code="core")
    assert payload["code"] == "core"
    assert payload["import_strategy"] == "osm_relation"
    assert payload["bbox"]["east"] == 20.99


def test_recover_scope_updates_existing_bbox_new(db_session, city_factory):
    _, dest, scope = destination_with_scope(db_session, city_factory, slug="recover-scope")
    candidate = candidate_from_input(_candidate_input(bbox={"south": 54.0, "west": 20.0, "north": 55.5, "east": 21.5}))
    updated, action = recover_or_create_scope(db_session, dest, candidate, code=scope.code, recover=True)
    assert action == "recovered"
    assert updated.id == scope.id
    assert updated.bbox["north"] == 55.5


def test_recover_scope_create_when_missing_new(db_session, city_factory):
    _, dest, _ = destination_with_scope(db_session, city_factory, slug="create-scope")
    candidate = candidate_from_input(_candidate_input(candidate_key="node:99", title="Новый контур"))
    scope, action = recover_or_create_scope(db_session, dest, candidate, code="new-core", recover=True)
    assert action == "created"
    assert scope.code == "new-core"


def test_recover_scope_conflict_without_recover_new(db_session, city_factory):
    _, dest, scope = destination_with_scope(db_session, city_factory, slug="scope-conflict")
    candidate = candidate_from_input(_candidate_input())
    with pytest.raises(ValueError):
        recover_or_create_scope(db_session, dest, candidate, code=scope.code, recover=False)


def test_invalid_bbox_rejected_new():
    with pytest.raises(ValidationIssue):
        candidate_from_input(_candidate_input(bbox={"south": 2, "north": 1, "west": 0, "east": 1}))
