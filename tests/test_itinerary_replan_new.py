from types import SimpleNamespace

from services import itinerary_replan_service as service
from schemas.itinerary_replan import (
    CurrentRouteContextInput,
    ItineraryReplanRequest,
    ReplanRoutePointInput,
)


def make_place(
    place_id: int,
    title: str,
    category: str = "walk",
    lat: float = 54.0,
    lng: float = 20.0,
    price_level: int | None = None,
):
    return SimpleNamespace(
        id=place_id,
        slug=f"place-{place_id}",
        title=title,
        category=category,
        lat=lat,
        lng=lng,
        price_level=price_level,
        is_active=True,
        city_id=1,
        opening_hours=None,
    )


def make_request(
    reason_type: str,
    completed_place_ids: list[int] | None = None,
    remaining_time_minutes: int | None = 120,
    new_time_budget_minutes: int | None = None,
    current_lat: float | None = 54.1,
    current_lng: float | None = 20.1,
    user_message: str | None = None,
    preferred_stop_place_id: int | None = None,
    budget_level: int | None = None,
) -> ItineraryReplanRequest:
    return ItineraryReplanRequest(
        current_route=CurrentRouteContextInput(
            city_slug="zelenogradsk",
            route_mode="walk",
            points=[
                ReplanRoutePointInput(
                    place_id=1,
                    position=1,
                    place_slug="p1",
                    place_title="Point 1",
                ),
                ReplanRoutePointInput(
                    place_id=2,
                    position=2,
                    place_slug="p2",
                    place_title="Point 2",
                ),
                ReplanRoutePointInput(
                    place_id=3,
                    position=3,
                    place_slug="p3",
                    place_title="Point 3",
                ),
            ],
            completed_place_ids=completed_place_ids or [],
            remaining_time_minutes=remaining_time_minutes,
            return_to_start=False,
            budget_level=budget_level,
        ),
        reason_type=reason_type,
        current_lat=current_lat,
        current_lng=current_lng,
        new_time_budget_minutes=new_time_budget_minutes,
        user_message=user_message,
        preferred_stop_place_id=preferred_stop_place_id,
    )


def setup_common_monkeypatches(monkeypatch, ordered_places):
    monkeypatch.setattr(
        service,
        "load_route_places",
        lambda db, current_route: ordered_places,
    )
    monkeypatch.setattr(
        service,
        "estimate_total_route_time_minutes",
        lambda places, merged_context, start_context: len(places) * 30,
    )
    monkeypatch.setattr(
        service,
        "estimate_total_route_distance_km",
        lambda places, start_context: round(len(places) * 1.2, 2),
    )


def test_new_replan_continue_from_here(monkeypatch):
    ordered_places = [
        make_place(1, "Museum"),
        make_place(2, "Promenade"),
        make_place(3, "Coffee"),
    ]
    setup_common_monkeypatches(monkeypatch, ordered_places)

    monkeypatch.setattr(
        service,
        "maybe_insert_stop_place",
        lambda db, request, remaining_places: (remaining_places, None),
    )
    monkeypatch.setattr(
        service,
        "rerank_places_for_replan",
        lambda places, request, start_context, city_timezone=None: places,
    )

    request = make_request(
        reason_type="continue_from_here",
        completed_place_ids=[1],
        budget_level=2,
    )

    response = service.replan_itinerary(db=None, request=request)

    assert response.status == "ok"
    assert len(response.points) == 2
    assert response.points[0].place_id == 2
    assert response.points[1].place_id == 3
    assert response.current_route_context is not None
    assert response.current_route_context.city_slug == "zelenogradsk"
    assert len(response.current_route_context.points) == 2
    assert response.current_route_context.points[0].place_id == 2
    assert response.current_route_context.points[1].place_id == 3
    assert response.current_route_context.completed_place_ids == [1]
    assert response.current_route_context.budget_level == 2


def test_new_replan_shorten_route(monkeypatch):
    ordered_places = [
        make_place(1, "Museum"),
        make_place(2, "Promenade"),
        make_place(3, "Coffee"),
    ]
    setup_common_monkeypatches(monkeypatch, ordered_places)

    monkeypatch.setattr(
        service,
        "maybe_insert_stop_place",
        lambda db, request, remaining_places: (remaining_places, None),
    )
    monkeypatch.setattr(
        service,
        "rerank_places_for_replan",
        lambda places, request, start_context, city_timezone=None: places,
    )

    request = make_request(
        reason_type="shorten_route",
        new_time_budget_minutes=60,
    )

    response = service.replan_itinerary(db=None, request=request)

    assert len(response.points) == 2
    assert response.points[0].place_id == 1
    assert response.points[1].place_id == 2
    assert response.estimated_remaining_minutes == 60
    assert response.current_route_context is not None
    assert response.current_route_context.remaining_time_minutes == 60


def test_new_replan_shorten_route_without_budget(monkeypatch):
    ordered_places = [
        make_place(1, "Museum"),
        make_place(2, "Promenade"),
    ]
    setup_common_monkeypatches(monkeypatch, ordered_places)

    request = make_request(
        reason_type="shorten_route",
        remaining_time_minutes=None,
        new_time_budget_minutes=None,
    )

    response = service.replan_itinerary(db=None, request=request)

    assert response.status == "ok"
    assert response.summary is not None
    assert "не был сокращен" in response.summary.lower()
    assert response.explanation is not None
    assert "time budget" in response.explanation.lower()


def test_new_replan_coffee_stop(monkeypatch):
    ordered_places = [
        make_place(1, "Museum", category="walk"),
        make_place(2, "Promenade", category="walk"),
    ]
    inserted_stop = make_place(99, "Best Coffee", category="cafe")

    setup_common_monkeypatches(monkeypatch, ordered_places)

    monkeypatch.setattr(
        service,
        "maybe_insert_stop_place",
        lambda db, request, remaining_places: ([inserted_stop, *remaining_places], inserted_stop),
    )
    monkeypatch.setattr(
        service,
        "rerank_places_for_replan",
        lambda places, request, start_context, city_timezone=None: places,
    )

    request = make_request(reason_type="coffee_stop", budget_level=1)

    response = service.replan_itinerary(db=None, request=request)

    assert response.points[0].place_id == 99
    assert "coffee stop" in (response.points[0].reason or "").lower()
    assert response.current_route_context is not None
    assert response.current_route_context.points[0].place_id == 99
    assert len(response.current_route_context.points) == 3
    assert response.current_route_context.budget_level == 1


def test_new_replan_food_stop(monkeypatch):
    ordered_places = [
        make_place(1, "Museum", category="walk"),
        make_place(2, "Promenade", category="walk"),
    ]
    inserted_stop = make_place(77, "Lunch Place", category="cafe")

    setup_common_monkeypatches(monkeypatch, ordered_places)

    monkeypatch.setattr(
        service,
        "maybe_insert_stop_place",
        lambda db, request, remaining_places: ([inserted_stop, *remaining_places], inserted_stop),
    )
    monkeypatch.setattr(
        service,
        "rerank_places_for_replan",
        lambda places, request, start_context, city_timezone=None: places,
    )

    request = make_request(reason_type="food_stop")

    response = service.replan_itinerary(db=None, request=request)

    assert response.points[0].place_id == 77
    assert "food stop" in response.summary.lower()
    assert response.current_route_context is not None
    assert response.current_route_context.points[0].place_id == 77


def test_new_replan_rest_stop(monkeypatch):
    ordered_places = [
        make_place(1, "Museum", category="walk"),
        make_place(2, "Promenade", category="walk"),
    ]
    inserted_stop = make_place(55, "Quiet Place", category="walk")

    setup_common_monkeypatches(monkeypatch, ordered_places)

    monkeypatch.setattr(
        service,
        "maybe_insert_stop_place",
        lambda db, request, remaining_places: ([inserted_stop, *remaining_places], inserted_stop),
    )
    monkeypatch.setattr(
        service,
        "rerank_places_for_replan",
        lambda places, request, start_context, city_timezone=None: places,
    )

    request = make_request(reason_type="rest_stop")

    response = service.replan_itinerary(db=None, request=request)

    assert response.points[0].place_id == 55
    assert response.explanation is not None
    assert "пауз" in response.explanation.lower()
    assert response.current_route_context is not None
    assert response.current_route_context.points[0].place_id == 55


def test_new_replan_custom(monkeypatch):
    ordered_places = [
        make_place(1, "Museum"),
        make_place(2, "Promenade"),
        make_place(3, "Coffee"),
    ]
    setup_common_monkeypatches(monkeypatch, ordered_places)

    monkeypatch.setattr(
        service,
        "maybe_insert_stop_place",
        lambda db, request, remaining_places: (remaining_places, None),
    )
    monkeypatch.setattr(
        service,
        "rerank_places_for_replan",
        lambda places, request, start_context, city_timezone=None: list(reversed(places)),
    )

    request = make_request(
        reason_type="custom",
        user_message="Хочу сначала кофе и что-то спокойное",
    )

    response = service.replan_itinerary(db=None, request=request)

    assert response.points[0].place_id == 3
    assert response.points[1].place_id == 2
    assert response.points[2].place_id == 1
    assert response.explanation is not None
    assert "текстовый запрос" in response.explanation.lower()
    assert response.current_route_context is not None
    assert response.current_route_context.points[0].place_id == 3


def test_new_replan_build_replan_merged_context_preserves_budget_level(monkeypatch):
    monkeypatch.setattr(
        service,
        "parse_route_intent",
        lambda user_message: {
            "preferences": {"interests": ["coffee"]},
            "constraints": {},
        },
    )

    request = make_request(
        reason_type="coffee_stop",
        budget_level=3,
    )

    merged_context = service.build_replan_merged_context(request)

    assert merged_context["budget_level"] == 3


def test_new_replan_find_best_stop_place_applies_budget_filter(monkeypatch):
    cheap = make_place(10, "Cheap Cafe", category="cafe", price_level=1)

    class FakeQuery:
        def __init__(self, items):
            self.items = items

        def filter(self, *args, **kwargs):
            return self

        def all(self):
            return self.items

    class FakeSession:
        def query(self, model):
            return FakeQuery([cheap])

    monkeypatch.setattr(
        service,
        "get_city_by_slug",
        lambda db, city_slug: SimpleNamespace(id=1, slug=city_slug),
    )

    db = FakeSession()

    result = service.find_best_stop_place(
        db=db,
        city_slug="zelenogradsk",
        reason_type="coffee_stop",
        anchor_lat=None,
        anchor_lng=None,
        exclude_place_ids=set(),
        budget_level=1,
    )

    assert result is not None
    assert result.id == 10
    assert result.price_level == 1
