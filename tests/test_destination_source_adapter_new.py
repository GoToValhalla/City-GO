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


def test_osm_overpass_candidate_never_fabricates_visit_duration_new(db_session, city_factory, monkeypatch):
    """CITYGO-265: _candidate_from_osm formerly hardcoded
    average_visit_duration_minutes=25 for every OSM-derived destination
    candidate, unconditionally -- OSM does not provide a real per-place
    visit duration, and the flat fabricated constant fed the same
    quality-score/coverage predicates as import_city_osm.py's own
    per-category fabrication."""
    _, dest, scope = destination_with_scope(db_session, city_factory, slug="source-no-fabrication")
    monkeypatch.delenv("CITYGO_DESTINATION_SOURCE_ADAPTER", raising=False)
    monkeypatch.setattr(
        "data.scripts.import_city_osm._fetch_osm_objects",
        lambda bbox, profile: [{"type": "node", "id": 2, "lat": 54.75, "lon": 20.5, "tags": {"amenity": "cafe", "name": "Кофе без выдумки"}}],
    )

    candidates = collect_scope_candidates(dest, scope)

    assert len(candidates) == 1
    assert "average_visit_duration_minutes" not in candidates[0].changes
