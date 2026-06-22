import pytest


pytestmark = [pytest.mark.admin, pytest.mark.routing, pytest.mark.api]


def test_route_readiness_eligibility_endpoint_counts_blockers(client, db_session, city_factory, place_factory):
    city = city_factory(slug="diag-city", name="Diag City")
    _ready(place_factory(slug="diag-ready", title="Ready", city_id=city.id, category="cafe"))
    _ready(place_factory(slug="diag-pharmacy", title="Pharmacy", city_id=city.id, category="pharmacy"))
    draft = _ready(place_factory(slug="diag-draft", title="Draft", city_id=city.id, category="park"))
    draft.is_published = False
    draft.publication_status = "draft"
    low = _ready(place_factory(slug="diag-low", title="Low", city_id=city.id, category="walk"))
    low.quality_score = 20
    no_photo = _ready(place_factory(slug="diag-no-photo", title="No Photo", city_id=city.id, category="museum"))
    no_photo.image_url = None
    no_address = _ready(place_factory(slug="diag-no-address", title="No Address", city_id=city.id, category="museum"))
    no_address.address = None
    db_session.commit()

    response = client.get("/admin/routes/eligibility/diag-city")

    assert response.status_code == 200
    payload = response.json()
    assert payload["city_slug"] == "diag-city"
    assert payload["places_total"] == 6
    assert payload["eligible_places"] == 1
    assert payload["published_places"] == 5
    assert payload["blockers_count_by_reason"]["hidden_category"] == 1
    assert payload["blockers_count_by_reason"]["draft_or_unpublished"] == 1
    assert payload["blockers_count_by_reason"]["low_quality"] == 1
    assert payload["blockers_count_by_reason"]["no_photo"] == 1
    assert payload["blockers_count_by_reason"]["no_address"] == 1


def test_near_ready_places_returns_places_with_one_or_two_blockers(client, db_session, city_factory, place_factory):
    city = city_factory(slug="near-ready-city")
    one = _ready(place_factory(slug="one-blocker", title="One", city_id=city.id, category="cafe"))
    one.image_url = None
    two = _ready(place_factory(slug="two-blockers", title="Two", city_id=city.id, category="park"))
    two.image_url = None
    two.address = None
    three = _ready(place_factory(slug="three-blockers", title="Three", city_id=city.id, category="pharmacy"))
    three.image_url = None
    three.address = None
    db_session.commit()

    payload = client.get("/admin/routes/eligibility/near-ready-city").json()

    slugs = {item["slug"] for item in payload["near_ready_places"]}
    assert slugs == {"one-blocker", "two-blockers"}
    assert "three-blockers" not in slugs


def test_fully_eligible_place_counted_correctly(client, db_session, city_factory, place_factory):
    city = city_factory(slug="eligible-city")
    _ready(place_factory(slug="eligible-place", title="Eligible", city_id=city.id, category="park"))
    db_session.commit()

    payload = client.get("/admin/routes/eligibility/eligible-city").json()

    assert payload["eligible_places"] == 1
    assert payload["sample_blocked_places"] == []


def _ready(place):
    place.image_url = "https://example.test/image.jpg"
    place.address = "Main street"
    place.quality_score = 80
    place.is_active = True
    place.status = "active"
    place.is_published = True
    place.is_visible_in_catalog = True
    place.is_route_eligible = True
    place.publication_status = "published"
    return place
