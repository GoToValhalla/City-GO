"""Regression for the route-eligibility bypass found in independent audit
of commit a79ad3a7: destination_import_service previously derived
route_eligible_when_published from `not service_only` (is_service_only_
category, i.e. exactly HARD_EXCLUDED_CATEGORIES) instead of the canonical
route-eligibility policy engine (services/route_eligibility_policy.py via
canonical_publication_apply.route_eligibility_verdict_for_publish). A
category outside both HARD_EXCLUDED_CATEGORIES and ALLOWED_ROUTE_CATEGORIES
(e.g. "zoo") would be marked is_route_eligible=True even though the policy
would reject it with "unknown_category". These tests prove the stored
flag now always matches the canonical policy verdict exactly."""

from __future__ import annotations

from models.place_publication_transition import PlacePublicationTransition
from services.canonical_publication_apply import route_eligibility_verdict_for_publish
from services.destination_candidate_adapter import DestinationCandidate
from services.destination_import_service import _upsert_candidate
from services.route_eligibility_policy import ALLOWED_ROUTE_CATEGORIES, HARD_EXCLUDED_CATEGORIES

from tests.destination_pipeline_helpers import destination_with_scope


def _candidate(**overrides) -> DestinationCandidate:
    base = dict(
        slug="route-policy-candidate",
        title="Тестовое место",
        category="museum",
        lat=54.75,
        lng=20.5,
        source="osm_overpass",
        changes={},
    )
    base.update(overrides)
    return DestinationCandidate(**base)


def test_allowed_route_category_is_route_eligible_new(db_session, city_factory) -> None:
    """"museum" is in ALLOWED_ROUTE_CATEGORIES and not in
    HARD_EXCLUDED_CATEGORIES -- the canonical policy marks it eligible,
    and the stored flag must match."""
    assert "museum" in ALLOWED_ROUTE_CATEGORIES
    assert "museum" not in HARD_EXCLUDED_CATEGORIES
    _, dest, scope = destination_with_scope(db_session, city_factory, slug="route-policy-allowed")
    counters: dict[str, int] = {"places_created": 0, "duplicates_skipped": 0, "memberships_created": 0, "memberships_updated": 0, "service_only_hidden": 0}

    place = _upsert_candidate(
        db_session, dest.legacy_city_id, dest, scope,
        _candidate(slug="route-policy-museum", category="museum"),
        counters,
    )
    db_session.commit()
    db_session.refresh(place)

    assert place.publication_status == "published"
    assert place.is_route_eligible is True
    assert place.route_exclusion_reason is None


def test_unknown_category_outside_route_policy_is_not_route_eligible_new(db_session, city_factory) -> None:
    """"zoo" is neither in HARD_EXCLUDED_CATEGORIES (so it is NOT
    service_only -- the place still gets published) nor in
    ALLOWED_ROUTE_CATEGORIES (so the canonical route-eligibility policy
    rejects it with "unknown_category"). Before this fix,
    route_eligible_when_published=not service_only would have marked this
    place is_route_eligible=True purely because it is not hard-excluded --
    a stored-flag/policy-verdict mismatch this test proves is now closed."""
    assert "zoo" not in HARD_EXCLUDED_CATEGORIES
    assert "zoo" not in ALLOWED_ROUTE_CATEGORIES
    _, dest, scope = destination_with_scope(db_session, city_factory, slug="route-policy-unknown")
    counters: dict[str, int] = {"places_created": 0, "duplicates_skipped": 0, "memberships_created": 0, "memberships_updated": 0, "service_only_hidden": 0}

    place = _upsert_candidate(
        db_session, dest.legacy_city_id, dest, scope,
        _candidate(slug="route-policy-zoo", category="zoo"),
        counters,
    )
    db_session.commit()
    db_session.refresh(place)

    # Still published -- "zoo" is not a service_only/hard-excluded category.
    assert place.publication_status == "published"
    assert place.is_published is True
    # But NOT route-eligible -- the canonical policy rejects unknown categories.
    assert place.is_route_eligible is False
    assert place.route_exclusion_reason is not None
    assert "unknown_category" in place.route_exclusion_reason


def test_service_only_category_is_hidden_and_not_route_eligible_new(db_session, city_factory) -> None:
    """"pharmacy" is in HARD_EXCLUDED_CATEGORIES -- is_service_only_category
    is True, the place is hidden (not published), and is_route_eligible is
    False via the writer's own hidden-status flag set, independent of the
    route policy engine (the policy is only consulted on the published
    path)."""
    assert "pharmacy" in HARD_EXCLUDED_CATEGORIES
    _, dest, scope = destination_with_scope(db_session, city_factory, slug="route-policy-service-only")
    counters: dict[str, int] = {"places_created": 0, "duplicates_skipped": 0, "memberships_created": 0, "memberships_updated": 0, "service_only_hidden": 0}

    place = _upsert_candidate(
        db_session, dest.legacy_city_id, dest, scope,
        _candidate(slug="route-policy-pharmacy", category="pharmacy"),
        counters,
    )
    db_session.commit()
    db_session.refresh(place)

    assert place.publication_status == "hidden"
    assert place.is_published is False
    assert place.is_route_eligible is False


def test_stored_route_eligible_flag_exactly_matches_canonical_policy_verdict_new(db_session, city_factory) -> None:
    """Direct parity proof across several categories: for every
    non-service_only category, the place's stored is_route_eligible must
    equal route_eligibility_verdict_for_publish's own verdict for a place
    already in its final published state -- not an approximation, the
    exact same policy answer."""
    categories = ["museum", "zoo", "park", "library", "cafe"]
    _, dest, scope = destination_with_scope(db_session, city_factory, slug="route-policy-parity")
    counters: dict[str, int] = {"places_created": 0, "duplicates_skipped": 0, "memberships_created": 0, "memberships_updated": 0, "service_only_hidden": 0}

    for category in categories:
        assert category not in HARD_EXCLUDED_CATEGORIES, f"{category} must not be service_only for this test"
        place = _upsert_candidate(
            db_session, dest.legacy_city_id, dest, scope,
            _candidate(slug=f"route-policy-parity-{category}", category=category),
            counters,
        )
        db_session.commit()
        db_session.refresh(place)

        canonical_verdict = route_eligibility_verdict_for_publish(place)
        assert place.is_route_eligible == canonical_verdict.eligible, (
            f"category={category}: stored is_route_eligible={place.is_route_eligible} "
            f"but canonical policy verdict={canonical_verdict.eligible} (reasons={canonical_verdict.reasons})"
        )


def test_route_eligible_published_place_has_exactly_one_transition_new(db_session, city_factory) -> None:
    """Publication mutation must still go through transition_place_publication
    only -- the route-policy lookup itself must not create any additional
    ledger row or bypass the canonical writer."""
    _, dest, scope = destination_with_scope(db_session, city_factory, slug="route-policy-single-transition")
    counters: dict[str, int] = {"places_created": 0, "duplicates_skipped": 0, "memberships_created": 0, "memberships_updated": 0, "service_only_hidden": 0}

    place = _upsert_candidate(
        db_session, dest.legacy_city_id, dest, scope,
        _candidate(slug="route-policy-single-transition-zoo", category="zoo"),
        counters,
    )
    db_session.commit()

    transitions = db_session.query(PlacePublicationTransition).filter_by(place_id=place.id).all()
    assert len(transitions) == 1
    assert transitions[0].actor == "destination_import"
    assert transitions[0].source == "destination_import"
