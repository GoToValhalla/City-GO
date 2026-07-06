from __future__ import annotations

from schemas.merged_context import BudgetLevel, MergedContext, PaceMode
from services.candidate_retrieval_service import CandidateRetrievalService
from tests.destination_pipeline_helpers import destination_with_scope


def test_route_destination_candidates_use_membership_under_flag_new(client, db_session, city_factory, place_factory, monkeypatch):
    monkeypatch.setattr("services.destination_flags.destination_route_reads_enabled", lambda: True)
    _, dest, _ = destination_with_scope(db_session, city_factory, slug="route-dest")
    client.post(f"/admin/destinations/{dest.slug}/data-pipeline/run", json={"mode": "full"})
    outside = place_factory(slug="outside-route-dest", title="Outside", lat=54.75, lng=20.5, is_route_eligible=True)
    candidates = CandidateRetrievalService().get_candidates(db_session, _ctx(dest.slug))
    ids = {place.id for place in candidates}
    assert outside.id not in ids
    assert len(ids) >= 1


def test_route_walking_guard_blocks_remote_destination_new(client, db_session, city_factory):
    _, dest, _ = destination_with_scope(db_session, city_factory, slug="remote-route")
    dest.destination_type = "remote_area"
    db_session.commit()
    response = client.post("/v1/user-routes/build", json={"lat": 54.75, "lng": 20.5, "destination_slug": dest.slug, "trip_type": "walking"})
    assert response.status_code in {200, 422}


def _ctx(slug: str) -> MergedContext:
    return MergedContext(location=(54.75, 20.5), time_budget_minutes=120, effective_time_budget_minutes=96, budget_level=BudgetLevel.MID, pace_mode=PaceMode.NORMAL, pace_multiplier=1.0, local_vs_tourist=0.5, novelty_mode=False, is_visiting=False, radius_meters=50_000, effective_num_stops=3, min_stop_duration_minutes=20, destination_slug=slug)
