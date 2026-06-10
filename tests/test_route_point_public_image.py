from types import SimpleNamespace

from schemas.merged_context import MergedContext
from services.route_point_factory import route_point_from_scored


def _ctx() -> MergedContext:
    return MergedContext(
        location=(54.96, 20.48),
        time_budget_minutes=120,
        effective_time_budget_minutes=96,
        budget_level=2,
        pace_mode="normal",
        pace_multiplier=1.0,
        local_vs_tourist=0.5,
        novelty_mode=False,
        is_visiting=False,
        radius_meters=1500,
        effective_num_stops=3,
        min_stop_duration_minutes=20,
    )


def test_route_point_uses_public_image_instead_of_legacy_place_image() -> None:
    place = SimpleNamespace(
        id=1,
        title="Place",
        address="Address",
        image_url="https://legacy.example/image.jpg",
        public_image_url="https://public.example/image.jpg",
        short_description=None,
        source=None,
        city=SimpleNamespace(slug="zelenogradsk"),
        lat=54.96,
        lng=20.48,
        category="cafe",
        average_visit_duration_minutes=30,
        opening_hours=None,
        validation=None,
        price_level=2,
    )
    scored = SimpleNamespace(place=place, score=0.9, breakdown={})

    point = route_point_from_scored(scored, _ctx(), SimpleNamespace)

    assert point.image_url == "https://public.example/image.jpg"
    assert point.city_slug == "zelenogradsk"
