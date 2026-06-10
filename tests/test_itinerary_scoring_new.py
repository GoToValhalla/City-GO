from types import SimpleNamespace

from services.itinerary_scoring_service import (
    build_place_text_blob,
    get_distance_from_start_km,
    rank_candidate_places,
    score_place,
    score_place_start_distance_fit,
)


def make_place(
    place_id: int,
    title: str,
    category: str = "walk",
    lat: float = 54.0,
    lng: float = 20.0,
    short_description: str | None = None,
    address: str | None = None,
    outdoor: bool = False,
    indoor: bool = False,
    dog_friendly: bool = False,
    family_friendly: bool = False,
    price_level: int | None = None,
):
    return SimpleNamespace(
        id=place_id,
        title=title,
        slug=f"place-{place_id}",
        category=category,
        lat=lat,
        lng=lng,
        short_description=short_description,
        address=address,
        outdoor=outdoor,
        indoor=indoor,
        dog_friendly=dog_friendly,
        family_friendly=family_friendly,
        price_level=price_level,
    )


def make_start_context(
    lat: float = 54.0,
    lng: float = 20.0,
    source: str = "geo_device",
):
    return SimpleNamespace(
        lat=lat,
        lng=lng,
        source=source,
    )


def test_new_scoring_build_place_text_blob_collects_main_fields():
    place = make_place(
        place_id=1,
        title="Sea Coffee",
        category="cafe",
        short_description="Best coffee near the beach",
        address="Promenade 1",
    )

    text_blob = build_place_text_blob(place)

    assert "sea coffee" in text_blob
    assert "best coffee near the beach" in text_blob
    assert "promenade 1" in text_blob
    assert "cafe" in text_blob


def test_new_scoring_get_distance_from_start_km_returns_none_without_start():
    place = make_place(place_id=1, title="Point")

    distance = get_distance_from_start_km(place=place, start_context=None)

    assert distance is None


def test_new_scoring_get_distance_from_start_km_returns_none_for_invalid_source():
    place = make_place(place_id=1, title="Point")
    start_context = make_start_context(source="invalid")

    distance = get_distance_from_start_km(place=place, start_context=start_context)

    assert distance is None


def test_new_scoring_start_distance_fit_gives_bonus_for_close_place():
    place = make_place(place_id=1, title="Near Point", lat=54.0005, lng=20.0005)
    start_context = make_start_context(lat=54.0, lng=20.0)

    score, reasons = score_place_start_distance_fit(
        place=place,
        start_context=start_context,
    )

    assert score > 0
    assert any("start point" in reason.lower() for reason in reasons)


def test_new_scoring_start_distance_fit_penalizes_far_place():
    place = make_place(place_id=1, title="Far Point", lat=54.2, lng=20.2)
    start_context = make_start_context(lat=54.0, lng=20.0)

    score, reasons = score_place_start_distance_fit(
        place=place,
        start_context=start_context,
    )

    assert score < 0
    assert any("far from start point" in reason.lower() for reason in reasons)


def test_new_scoring_score_place_respects_budget_level():
    place = make_place(
        place_id=1,
        title="Expensive Cafe",
        category="cafe",
        price_level=5,
    )

    merged_context = {
        "preferences": {"interests": ["coffee"]},
        "budget_level": 2,
        "route_mode": "walk",
    }

    result = score_place(
        place=place,
        merged_context=merged_context,
        start_context=None,
    )

    assert result["score"] < 3.0
    assert any("above budget preference" in reason.lower() for reason in result["reasons"])


def test_new_scoring_rank_candidate_places_prefers_near_start_when_otherwise_similar():
    near_place = make_place(
        place_id=1,
        title="Near Cafe",
        category="cafe",
        lat=54.0005,
        lng=20.0005,
        price_level=1,
    )
    far_place = make_place(
        place_id=2,
        title="Far Cafe",
        category="cafe",
        lat=54.08,
        lng=20.08,
        price_level=1,
    )

    merged_context = {
        "preferences": {"interests": ["coffee"]},
        "budget_level": 2,
        "route_mode": "walk",
    }
    start_context = make_start_context(lat=54.0, lng=20.0)

    ranked = rank_candidate_places(
        candidate_places=[far_place, near_place],
        merged_context=merged_context,
        start_context=start_context,
    )

    assert ranked[0]["place"].id == 1
    assert ranked[1]["place"].id == 2


def test_new_scoring_rank_candidate_places_keeps_default_reason_when_no_signal():
    neutral_place = make_place(
        place_id=1,
        title="Neutral Point",
        category="misc",
        price_level=None,
    )

    merged_context = {
        "preferences": {"interests": []},
        "route_mode": None,
        "budget_level": None,
    }

    ranked = rank_candidate_places(
        candidate_places=[neutral_place],
        merged_context=merged_context,
        start_context=None,
    )

    assert len(ranked) == 1
    assert ranked[0]["place"].id == 1
    assert ranked[0]["reasons"] == ["Selected as a generally suitable place candidate"]
