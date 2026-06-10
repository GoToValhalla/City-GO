from types import SimpleNamespace

from schemas.merged_context import BudgetLevel, MergedContext, PaceMode
from services.route_assembly_optimizer import assemble_route
from services.scoring_service import ScoredPlace


class TestRoutePoint:
    def __init__(
        self,
        place_id,
        lat,
        lng,
        score,
        category,
        visit_minutes,
        opening_hours=None,
        validation=None,
        price_level=None,
        scoring_breakdown=None,
        title=None,
        address=None,
        image_url=None,
        short_description=None,
        source=None,
        city_slug=None,
    ):
        self.place_id = place_id
        self.lat = lat
        self.lng = lng
        self.score = score
        self.category = category
        self.visit_minutes = visit_minutes
        self.opening_hours = opening_hours
        self.validation = validation
        self.price_level = price_level
        self.scoring_breakdown = scoring_breakdown or {}
        self.title = title
        self.address = address
        self.image_url = image_url
        self.short_description = short_description
        self.source = source
        self.city_slug = city_slug


def _ctx(time_budget_minutes=120):
    return MergedContext(
        location=(54.96, 20.48),
        city_id="zelenogradsk",
        time_budget_minutes=time_budget_minutes,
        effective_time_budget_minutes=int(time_budget_minutes * 0.8),
        time_of_day=None,
        route_time_mode="flexible",
        interests=["walk", "sea"],
        avoided_categories=[],
        avoided_place_ids=[],
        budget_level=BudgetLevel.MID,
        pace_mode=PaceMode.NORMAL,
        pace_multiplier=1.0,
        local_vs_tourist=0.5,
        novelty_mode=False,
        is_visiting=False,
        visit_city_id=None,
        visit_days=1,
        radius_meters=1500,
        effective_num_stops=3,
        min_stop_duration_minutes=20,
    )


def _place(place_id, title, lat, lng, category, visit_minutes, score):
    place = SimpleNamespace(
        id=place_id,
        title=title,
        lat=lat,
        lng=lng,
        category=category,
        average_visit_duration_minutes=visit_minutes,
        effective_visit_duration_minutes=visit_minutes,
        opening_hours=None,
        effective_opening_hours={"mon": {"open": "00:00", "close": "23:59"}},
        price_level=1,
        public_image_url=None,
        short_description=None,
        source="test",
        city=SimpleNamespace(slug="zelenogradsk"),
        validation={"is_valid": True, "issues": []},
    )
    return ScoredPlace(place, score, {"test": score})


def test_assembly_relaxes_budget_when_one_point_would_stop_route_new():
    scored = [
        _place(1, "Променад", 54.9601, 20.4801, "walk", 45, 0.95),
        _place(2, "Кофе", 54.9602, 20.4802, "cafe", 30, 0.85),
        _place(3, "Сквер", 54.9603, 20.4803, "walk", 45, 0.80),
    ]

    route = assemble_route(scored, _ctx(120), TestRoutePoint)

    assert len(route) >= 2
    assert route[0].place_id == "1"


def test_assembly_keeps_empty_route_when_candidates_absent_new():
    route = assemble_route([], _ctx(120), TestRoutePoint)

    assert route == []
