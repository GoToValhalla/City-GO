from __future__ import annotations

from types import SimpleNamespace

import pytest

from services.route_diversity_policy import normalize_category
from services.route_eligibility_policy import (
    ALLOWED_ROUTE_CATEGORIES,
    HARD_EXCLUDED_CATEGORIES,
    evaluate_place_route_eligibility,
)


def _place(**updates: object) -> SimpleNamespace:
    payload = {
        "city_id": 1,
        "title": "City museum",
        "canonical_category": "museum",
        "category": "museum",
        "category_ref": None,
        "lat": 43.238949,
        "lng": 76.889709,
        "is_active": True,
        "status": "active",
        "lifecycle_status": "active",
        "is_published": True,
        "is_visible_in_catalog": True,
        "is_route_eligible": True,
        "publication_status": "published",
        "place_layer": "tourist_catalog",
        "tourist_eligible": True,
        "transport_required": False,
        "route_policy": "city_walking",
        "quality_tier": "silver",
        "is_spam_poi": False,
        "is_duplicate_suspected": False,
        "critical_field_expired": False,
    }
    payload.update(updates)
    return SimpleNamespace(**payload)


@pytest.mark.parametrize("category", sorted(HARD_EXCLUDED_CATEGORIES))
def test_route_eligibility_rejects_every_hard_excluded_category_new(category: str) -> None:
    verdict = evaluate_place_route_eligibility(_place(canonical_category=category, category="museum"))
    normalized = normalize_category(category)

    assert verdict.eligible is False
    assert f"hard_excluded_category:{normalized}" in verdict.reasons
    assert verdict.canonical_category == normalized
    assert verdict.admin_bucket == "route_excluded"


@pytest.mark.parametrize("category", sorted(ALLOWED_ROUTE_CATEGORIES))
def test_route_eligibility_accepts_allowed_categories_with_valid_quality_new(category: str) -> None:
    verdict = evaluate_place_route_eligibility(_place(canonical_category=category, category="display_noise"))
    normalized = normalize_category(category)

    assert verdict.eligible is True
    assert verdict.reasons == ()
    assert verdict.canonical_category == normalized


@pytest.mark.parametrize(
    "title",
    [
        "Место для прогулки OSM 123",
        "Place for walk OSM 123",
        "OSM node 123",
        "Node 4829103",
        "Way 4829103",
        "Unnamed POI",
        "Unnamed place",
        "Без названия",
        "Место без названия",
    ],
)
def test_route_eligibility_rejects_generic_osm_placeholder_titles_new(title: str) -> None:
    verdict = evaluate_place_route_eligibility(_place(title=title, canonical_category="park"))

    assert verdict.eligible is False
    assert "generic_osm_placeholder" in verdict.reasons


@pytest.mark.parametrize(
    "field,value,reason",
    [
        ("city_id", None, "missing_city_id"),
        ("is_active", False, "inactive"),
        ("status", "hidden", "place_status_not_active"),
        ("lifecycle_status", "archived", "lifecycle_not_active"),
        ("is_published", False, "draft_or_unpublished"),
        ("is_visible_in_catalog", False, "not_visible_in_catalog"),
        ("lat", None, "missing_coordinates"),
        ("lng", None, "missing_coordinates"),
        ("place_layer", "infra_only", "non_tourist_place_layer"),
        ("tourist_eligible", False, "not_tourist_eligible"),
        ("transport_required", True, "transport_required_scope"),
        ("route_policy", "transfer_only", "non_walking_route_policy"),
        ("quality_tier", "bad", "quality_tier_not_route_allowed:bad"),
        ("is_spam_poi", True, "spam_poi"),
        ("is_duplicate_suspected", True, "duplicate_suspected"),
        ("critical_field_expired", True, "critical_field_expired"),
        ("publication_status", "archived", "place_archived"),
    ],
)
def test_route_eligibility_rejects_invalid_public_route_state_new(field: str, value: object, reason: str) -> None:
    verdict = evaluate_place_route_eligibility(_place(**{field: value}))

    assert verdict.eligible is False
    assert reason in verdict.reasons


def test_route_eligibility_allows_bronze_quality_for_runtime_route_recall_new() -> None:
    verdict = evaluate_place_route_eligibility(_place(quality_tier="bronze"))

    assert verdict.eligible is True
    assert verdict.reasons == ()


def test_route_eligibility_requires_stored_flag_when_requested_new() -> None:
    verdict = evaluate_place_route_eligibility(_place(is_route_eligible=False), require_stored_flag=True)

    assert verdict.eligible is False
    assert "route_eligible_not_true" in verdict.reasons


def test_route_eligibility_ignores_stored_flag_for_policy_preview_when_not_required_new() -> None:
    verdict = evaluate_place_route_eligibility(_place(is_route_eligible=False), require_stored_flag=False)

    assert verdict.eligible is True


def test_route_eligibility_uses_canonical_category_over_display_category_new() -> None:
    verdict = evaluate_place_route_eligibility(_place(canonical_category="museum", category="display_noise"))

    assert verdict.eligible is True
    assert verdict.canonical_category == "museum"


def test_route_eligibility_blocks_canonical_category_even_when_display_category_is_allowed_new() -> None:
    verdict = evaluate_place_route_eligibility(_place(canonical_category="health", category="museum"))

    assert verdict.eligible is False
    assert "hard_excluded_category:health" in verdict.reasons


def test_route_eligibility_unknown_category_gets_route_unknown_bucket_new() -> None:
    verdict = evaluate_place_route_eligibility(_place(canonical_category="random_osm_tag", category="museum"))

    assert verdict.eligible is False
    assert "unknown_category" in verdict.reasons
    assert verdict.admin_bucket == "route_unknown"


def test_route_eligibility_rejects_unpublished_city_new() -> None:
    verdict = evaluate_place_route_eligibility(_place(), city=SimpleNamespace(is_active=True, launch_status="draft"))

    assert verdict.eligible is False
    assert "city_not_published" in verdict.reasons


def test_route_eligibility_rejects_inactive_city_new() -> None:
    verdict = evaluate_place_route_eligibility(_place(), city=SimpleNamespace(is_active=False, launch_status="published"))

    assert verdict.eligible is False
    assert "city_inactive" in verdict.reasons
