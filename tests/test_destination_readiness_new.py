from __future__ import annotations

from models.place_merge_review import ReviewItem
from tests.destination_pipeline_helpers import destination_with_scope


def test_destination_readiness_metrics_and_degraded_sections_new(client, db_session, city_factory):
    _, dest, _ = destination_with_scope(db_session, city_factory, slug="ready-dest")
    client.post(f"/admin/destinations/{dest.slug}/data-pipeline/run", json={"mode": "import_only"})
    response = client.get(f"/admin/destinations/{dest.slug}/readiness")
    assert response.status_code == 200
    payload = response.json()
    assert payload["places_total"] == 3
    assert payload["published_places"] == 2
    assert payload["service_only_hidden"] == 1
    assert "photo" in payload["degraded_sections"]


def test_destination_readiness_counts_pending_reviews_new(client, db_session, city_factory):
    _, dest, _ = destination_with_scope(db_session, city_factory, slug="review-ready")
    client.post(f"/admin/destinations/{dest.slug}/data-pipeline/run", json={"mode": "import_only"})
    place_id = client.get(f"/admin/destinations/{dest.slug}/memberships").json()[0]["place_id"]
    db_session.add(ReviewItem(place_id=place_id, proposed_diff={"address": {"proposed": "x"}}, place_version_at_creation=1, status="pending"))
    db_session.commit()
    assert client.get(f"/admin/destinations/{dest.slug}/readiness").json()["pending_reviews"] == 1
