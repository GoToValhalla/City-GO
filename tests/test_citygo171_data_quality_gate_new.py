from __future__ import annotations

import json

import pytest

from models.route_draft import RouteDraft
from scripts.production_smoke import validate_route_response
from services.admin_overview_service import build_admin_overview
from services.osm_import_taxonomy import category_from_osm_tags, classify_osm_place
from services.place_quality_signals import is_placeholder_title
from services.route_draft_errors import RouteDraftError
from services.route_draft_loader import eligible_place_or_error
from services.route_eligibility import evaluate_place_route_eligibility, route_eligible_sql_conditions
from models.place import Place


def test_citygo171_policy_fails_closed_without_canonical_category_new(db_session, place_factory) -> None:
    place = place_factory(category="park", title="Display Park")
    place.canonical_category = None
    place.category_id = None
    db_session.commit()

    verdict = evaluate_place_route_eligibility(place)
    visible = db_session.query(Place).filter(Place.id == place.id, *route_eligible_sql_conditions()).first()

    assert verdict.eligible is False
    assert "unknown_category" in verdict.reasons
    assert visible is None


def test_citygo171_sql_and_python_policy_agree_for_safe_and_blocked_places_new(
    db_session,
    place_factory,
) -> None:
    safe = place_factory(slug="safe-park", title="Safe Park", category="park")
    safe.canonical_category = "park"
    blocked = place_factory(slug="blocked-hospital", title="Институт хирургии им. Микаеляна", category="hospital")
    blocked.canonical_category = "hospital"
    unknown = place_factory(slug="unknown-category", title="Unknown", category="park")
    unknown.canonical_category = None
    unknown.category_id = None
    db_session.commit()

    sql_ids = {
        row.id
        for row in db_session.query(Place).filter(
            Place.id.in_([safe.id, blocked.id, unknown.id]),
            *route_eligible_sql_conditions(),
        )
    }
    python_ids = {
        place.id
        for place in (safe, blocked, unknown)
        if evaluate_place_route_eligibility(place).eligible
    }

    assert sql_ids == python_ids == {safe.id}


def test_citygo171_admin_overview_exposes_excluded_and_unknown_route_buckets_new(
    db_session,
    place_factory,
) -> None:
    place_factory(slug="route-false", is_route_eligible=False, is_published=True)

    overview = build_admin_overview(db_session)
    card = next(item for item in overview["data_quality"] if item.code == "not_route_eligible")
    unknown_card = next(item for item in overview["data_quality"] if item.code == "route_unknown")

    assert card.count >= 1
    assert unknown_card.count >= 0


@pytest.mark.parametrize(
    "title",
    [
        "Место для прогулки OSM 123",
        "Place for walk OSM 123",
        "OSM 123",
        "Culture OSM 123",
        "Node 123",
        "Way 456",
        "Unnamed POI",
        "Unnamed place",
    ],
)
def test_citygo171_generic_osm_titles_are_placeholders_new(title: str) -> None:
    assert is_placeholder_title(title) is True


def test_citygo171_real_short_titles_are_not_placeholders_new() -> None:
    assert is_placeholder_title("Парк") is False
    assert is_placeholder_title("Пляж") is False


def test_citygo171_osm_medical_tags_beat_wikidata_shortcut_new() -> None:
    tags = {"amenity": "hospital", "wikidata": "Q123", "wikipedia": "ru:Hospital"}

    classification = classify_osm_place(tags)

    assert category_from_osm_tags(tags) == "health"
    assert classification.is_route_eligible is False
    assert classification.tourist_eligible is False
    assert classification.route_exclusion_reason == "not_tourist_poi"


def test_citygo171_manual_add_rejects_hard_excluded_place_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="manual-guard")
    place = place_factory(
        city_id=city.id,
        slug="manual-hospital",
        title="Институт хирургии им. Микаеляна",
        category="hospital",
        is_route_eligible=True,
    )
    place.canonical_category = "hospital"
    draft = RouteDraft(city_id=city.id, random_seed=7, start_lat=1.0, start_lng=1.0, budget_minutes=120)
    db_session.add(draft)
    db_session.commit()

    with pytest.raises(RouteDraftError) as exc:
        eligible_place_or_error(db_session, city.id, place.id)

    assert exc.value.code == "PLACE_NOT_ELIGIBLE"


def test_citygo171_production_smoke_rejects_generic_and_huge_budget_overflow_new() -> None:
    payload = {
        "status": "ready",
        "total_places": 3,
        "total_estimated_minutes": 284,
        "time_budget_minutes": 120,
        "points": [
            {"place_id": "1", "title": "Место для прогулки OSM 123", "category": "walk"},
            {"place_id": "2", "title": "Институт хирургии им. Микаеляна", "category": "medical"},
            {"place_id": "3", "title": "Парк", "category": "park"},
        ],
    }

    result = validate_route_response(json.dumps(payload, ensure_ascii=False), 200)

    assert result.failed
    assert result.detail in {"route_contains_forbidden_junk", "route_budget_overflow"}
