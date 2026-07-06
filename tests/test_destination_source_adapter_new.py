from __future__ import annotations

from services.destination_candidate_adapter import collect_scope_candidates
from tests.destination_pipeline_helpers import destination_with_scope


def test_destination_source_default_uses_osm_overpass_adapter_new(db_session, city_factory, monkeypatch):
    _, dest, scope = destination_with_scope(db_session, city_factory, slug="source-real")
    monkeypatch.delenv("CITYGO_DESTINATION_SOURCE_ADAPTER", raising=False)
    monkeypatch.setattr(
        "data.scripts.import_city_osm._fetch_osm_objects",
        lambda bbox, profile: [{"type": "node", "id": 1, "lat": 54.75, "lon": 20.5, "tags": {"amenity": "cafe", "name": "Кофе"}}],
    )
    candidates = collect_scope_candidates(dest, scope)
    assert len(candidates) == 1
    assert candidates[0].source == "osm_overpass"
    assert candidates[0].title == "Кофе"
