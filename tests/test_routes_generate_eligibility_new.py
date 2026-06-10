"""Интеграция eligibility с /routes/generate и /routes/replan."""

from __future__ import annotations

from schemas.itinerary import ItineraryGenerateRequest
from schemas.itinerary_replan import CurrentRouteContextInput, ItineraryReplanRequest
from services.itinerary_candidate_service import get_candidate_places
from services.itinerary_replan_service import find_best_stop_place


def test_generate_candidates_exclude_pharmacy_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="gen-elig-city")
    cafe = place_factory(slug="gen-cafe", category="cafe", city_id=city.id)
    place_factory(slug="gen-pharm", category="pharmacy", city_id=city.id)
    request = ItineraryGenerateRequest(city_slug=city.slug, time_budget_minutes=120)
    candidates = get_candidate_places(db_session, request, merged_context={}, start_context=None)
    ids = {place.id for place in candidates}
    assert cafe.id in ids
    assert all(place.category != "pharmacy" for place in candidates)


def test_replan_stop_search_excludes_pharmacy_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="repl-elig-city")
    place_factory(slug="repl-cafe", category="cafe", city_id=city.id, lat=54.96, lng=20.47)
    place_factory(slug="repl-pharm", category="pharmacy", city_id=city.id, lat=54.961, lng=20.471)
    stop = find_best_stop_place(
        db_session,
        city_slug=city.slug,
        reason_type="coffee_stop",
        anchor_lat=54.96,
        anchor_lng=20.47,
        exclude_place_ids=set(),
    )
    if stop is not None:
        assert stop.category != "pharmacy"
