"""Regression tests for a defect discovered during CITYGO-357 inventory (not
one of the two originally reported bugs — proven here per the task's "prove
root cause with a failing regression test before fixing" rule).

Root cause: the legacy itinerary stack (routers/itinerary.py's deprecated
POST /routes/generate and still-active POST /routes/replan) is a fully
public, unauthenticated entrypoint. Its candidate/place-reload retrieval
(services/itinerary_candidate_service.py::get_candidate_places,
services/itinerary_replan_service.py::load_route_places and
load_preferred_stop_place) used
services.route_eligibility.apply_route_eligible_filters() — the same
PLACE-LEVEL-ONLY filter identified as the CITYGO-355 root cause in
CandidateRetrievalService — with no city publication check anywhere in the
call path. get_city_by_slug() in both modules resolves any city by slug
with no launch_status/is_active check, so a preview, preparing, hidden,
archived, disabled, or inactive city's places were fully eligible.

(services/itinerary_replan_service.py::find_best_stop_place was NOT part of
this defect: it separately calls
evaluate_place_route_eligibility(place, city=city), which does check
city.launch_status/is_active via its internal _city_reason() helper — this
was verified directly before writing these tests, to avoid asserting a
defect that does not actually exist there.)

Fix: get_candidate_places, load_route_places, and load_preferred_stop_place
now use apply_public_route_eligible_filters(), the canonical composition of
public_place_conditions() (city publication + place visibility) with
place-level route eligibility — the same helper CandidateRetrievalService
and the route-draft/random-route stack now use.
"""

from __future__ import annotations

from schemas.itinerary import ItineraryGenerateRequest
from schemas.itinerary_replan import CurrentRoutePointInput
from services.itinerary_candidate_service import get_candidate_places
from services.itinerary_replan_service import load_preferred_stop_place, load_route_places


class _RouteContext:
    def __init__(self, points):
        self.points = points


def test_generate_candidates_excludes_preview_city_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="itin-preview-city", launch_status="preview")
    place_factory(slug="itin-preview-cafe", category="cafe", city_id=city.id)

    request = ItineraryGenerateRequest(city_slug=city.slug, time_budget_minutes=120)
    candidates = get_candidate_places(db_session, request, merged_context={}, start_context=None)

    assert candidates == []


def test_generate_candidates_excludes_preparing_city_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="itin-preparing-city", launch_status="preparing")
    place_factory(slug="itin-preparing-cafe", category="cafe", city_id=city.id)

    request = ItineraryGenerateRequest(city_slug=city.slug, time_budget_minutes=120)
    candidates = get_candidate_places(db_session, request, merged_context={}, start_context=None)

    assert candidates == []


def test_generate_candidates_includes_published_city_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="itin-published-city", launch_status="published")
    cafe = place_factory(slug="itin-published-cafe", category="cafe", city_id=city.id)

    request = ItineraryGenerateRequest(city_slug=city.slug, time_budget_minutes=120)
    candidates = get_candidate_places(db_session, request, merged_context={}, start_context=None)

    assert {place.id for place in candidates} == {cafe.id}


def test_load_route_places_excludes_preview_city_place_new(db_session, city_factory, place_factory) -> None:
    """A route re-loaded during replan must not resurrect a place whose city
    has since moved to preview (or never left it)."""
    city = city_factory(slug="itin-replan-load-preview-city", launch_status="preview")
    place = place_factory(slug="itin-replan-load-preview-place", category="cafe", city_id=city.id)

    current_route = _RouteContext(points=[CurrentRoutePointInput(place_id=place.id, position=1)])
    ordered_places, missing_ids = load_route_places(db_session, current_route)

    assert ordered_places == []
    assert missing_ids == [place.id]


def test_load_route_places_includes_published_city_place_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="itin-replan-load-published-city", launch_status="published")
    place = place_factory(slug="itin-replan-load-published-place", category="cafe", city_id=city.id)

    current_route = _RouteContext(points=[CurrentRoutePointInput(place_id=place.id, position=1)])
    ordered_places, missing_ids = load_route_places(db_session, current_route)

    assert [p.id for p in ordered_places] == [place.id]
    assert missing_ids == []


def test_load_preferred_stop_place_excludes_preview_city_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="itin-preferred-stop-preview-city", launch_status="preview")
    place = place_factory(slug="itin-preferred-stop-preview-place", category="cafe", city_id=city.id)

    result = load_preferred_stop_place(
        db_session,
        city_slug=city.slug,
        preferred_stop_place_id=place.id,
        exclude_place_ids=set(),
        target_categories=None,
    )

    assert result is None


def test_load_preferred_stop_place_includes_published_city_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="itin-preferred-stop-published-city", launch_status="published")
    place = place_factory(slug="itin-preferred-stop-published-place", category="cafe", city_id=city.id)

    result = load_preferred_stop_place(
        db_session,
        city_slug=city.slug,
        preferred_stop_place_id=place.id,
        exclude_place_ids=set(),
        target_categories=None,
    )

    assert result is not None
    assert result.id == place.id
