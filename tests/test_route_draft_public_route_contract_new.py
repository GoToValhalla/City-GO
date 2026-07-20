"""Regression tests for a defect discovered during CITYGO-357 inventory (not
one of the two originally reported bugs — proven here per the task's "prove
root cause with a failing regression test before fixing" rule).

Root cause: services/route_draft_rules.py::eligible_place_query() (used by
the fully public, unauthenticated POST /routes/random,
GET/POST /routes/drafts/{id}/*, and GET /routes/drafts/{id}/search-places
endpoints in routers/route_drafts.py) built its query with
`compile_route_eligible_sql_conditions()` — the same PLACE-LEVEL-ONLY
condition set identified as the CITYGO-355 root cause in
CandidateRetrievalService — and never joined City at all, so it applied NO
city publication gate whatsoever (not even the partial
BLOCKED_CITY_LAUNCH_STATUSES check CITYGO-355 replaced). A random/drafted
route could be built entirely from a preview, preparing, hidden, archived,
disabled, or inactive city.

Fix: eligible_place_query() now joins City and requires
City.is_active AND City.launch_status == "published", reusing the same
public_place_conditions()-backed contract as CandidateRetrievalService,
instead of duplicating a separate, weaker rule.
"""

from __future__ import annotations

from sqlalchemy import select

from models.place import Place
from services.route_draft_rules import eligible_place_query


def test_preview_city_places_excluded_from_eligible_query_new(db_session, city_factory, published_place_factory) -> None:
    city = city_factory(slug="draft-preview-city", launch_status="preview")
    published_place_factory(city_id=city.id, lat=54.9611, lng=20.4703)

    query = eligible_place_query(db_session.query(Place), city.id)

    assert query.all() == []


def test_preparing_city_places_excluded_from_eligible_query_new(db_session, city_factory, published_place_factory) -> None:
    city = city_factory(slug="draft-preparing-city", launch_status="preparing")
    published_place_factory(city_id=city.id, lat=54.9611, lng=20.4703)

    query = eligible_place_query(db_session.query(Place), city.id)

    assert query.all() == []


def test_published_city_places_still_returned_new(db_session, city_factory, published_place_factory) -> None:
    city = city_factory(slug="draft-published-city", launch_status="published")
    place = published_place_factory(city_id=city.id, lat=54.9611, lng=20.4703)

    query = eligible_place_query(db_session.query(Place), city.id)
    result_ids = {row.id for row in query.all()}

    assert place.id in result_ids


def test_inactive_city_places_excluded_from_eligible_query_new(db_session, city_factory, published_place_factory) -> None:
    city = city_factory(slug="draft-inactive-city", launch_status="published", is_active=False)
    published_place_factory(city_id=city.id, lat=54.9611, lng=20.4703)

    query = eligible_place_query(db_session.query(Place), city.id)

    assert query.all() == []


def test_random_route_endpoint_returns_no_places_for_preview_city_new(client, city_factory, published_place_factory) -> None:
    city = city_factory(slug="draft-preview-endpoint-city", launch_status="preview")
    published_place_factory(city_id=city.id, lat=54.9611, lng=20.4703, category="cafe")

    response = client.post(
        "/routes/random",
        json={
            "city_slug": city.slug,
            "budget_minutes": 120,
            "start": {"type": "city_center", "label": "Центр города"},
            "category_mode": "none",
            "selected_category_slugs": [],
            "seed": 42,
            "session_token": "preview-city-token-01",
        },
    )

    # Unpublished city is treated as not found at the public create boundary.
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "CITY_NOT_FOUND"
