from models.place_photo_candidate import PlacePhotoCandidate


def test_import_pipeline_admin_endpoints_new(client, db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="pipeline-api")
    place = place_factory(city_id=city.id, slug="api-place", title="API Place", category="park", address=None)
    place.source = "category_fallback"
    place.confidence = 0.9
    place.image_url = "https://example.test/api.jpg"
    db_session.commit()

    run = client.post(f"/admin/place-enrichment/pipeline/{city.slug}/run")
    assert run.status_code == 200
    payload = run.json()
    assert payload["city_slug"] == city.slug
    assert payload["counters"]["found"] == 1

    steps = client.get(f"/admin/place-enrichment/jobs/{payload['job_id']}/steps")
    assert steps.status_code == 200
    assert {item["step_name"] for item in steps.json()} >= {"collect_places", "apply_publication_decisions"}

    confidence = client.get(f"/admin/place-enrichment/places/{place.id}/confidence")
    assert confidence.status_code == 200
    assert {item["field_name"] for item in confidence.json()} >= {"title", "address", "photo"}

    review = client.get(f"/admin/place-enrichment/review-queue?city_slug={city.slug}")
    assert review.status_code == 200
    assert review.json()

    resolved = client.post(f"/admin/place-enrichment/review-queue/{review.json()[0]['id']}/resolve", json={"resolution": "fixed"})
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"

    candidate = db_session.query(PlacePhotoCandidate).filter_by(place_id=place.id).one()
    primary = client.post(f"/admin/place-enrichment/photo-candidates/{candidate.id}/set-primary")
    assert primary.status_code == 400
