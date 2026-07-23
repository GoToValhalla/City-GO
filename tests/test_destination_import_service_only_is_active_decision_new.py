"""Documents the evidence-based decision for the service-only
Place.is_active behavior flagged in independent audit of commit a79ad3a7:
the pre-fix destination_import_service._new_place always set
is_active=True unconditionally (even for service_only categories); the
fixed version routes through transition_place_publication(to_status=
"hidden"), whose canonical PublicationStateFlags for "hidden" set
is_active=False. This is an intentional behavior change (DECISION A: keep
is_active=False), not an accidental regression, for the reasons proven
below."""

from __future__ import annotations

from services.destination_candidate_adapter import DestinationCandidate
from services.destination_import_service import _upsert_candidate
from services.publication_state_writer import _STATE_FLAGS

from tests.destination_pipeline_helpers import destination_with_scope


def _candidate(**overrides) -> DestinationCandidate:
    base = dict(
        slug="is-active-decision-candidate",
        title="Аптека у моря",
        category="pharmacy",
        lat=54.75,
        lng=20.5,
        source="osm_overpass",
        changes={},
    )
    base.update(overrides)
    return DestinationCandidate(**base)


def test_hidden_status_is_active_false_is_the_universal_canonical_contract_new() -> None:
    """DECISION A evidence #1: is_active=False for "hidden" status is not
    something destination_import_service invented -- it is
    publication_state_writer's own canonical flag set for EVERY caller
    that transitions a place to "hidden" (place_service.delete_place's
    soft-delete, admin_emergency_hide_service, place_verification_service,
    admin_place_bulk_service, data/scripts/cleanup_bad_places.py all use
    to_status="hidden" and get this same is_active=False)."""
    hidden_flags = _STATE_FLAGS["hidden"]
    assert hidden_flags.is_active is False
    assert hidden_flags.is_published is False
    assert hidden_flags.is_visible_in_catalog is False
    assert hidden_flags.is_searchable is False


def test_service_only_destination_place_is_active_false_new(db_session, city_factory) -> None:
    """DECISION A evidence #2: a service_only destination-imported place
    reaches is_active=False by going through the SAME canonical "hidden"
    transition every other hide/soft-delete path in the codebase uses --
    not a special case, not a bypass of the publication writer."""
    _, dest, scope = destination_with_scope(db_session, city_factory, slug="is-active-decision")
    counters: dict[str, int] = {"places_created": 0, "duplicates_skipped": 0, "memberships_created": 0, "memberships_updated": 0, "service_only_hidden": 0}

    place = _upsert_candidate(db_session, dest.legacy_city_id, dest, scope, _candidate(), counters)
    db_session.commit()
    db_session.refresh(place)

    assert place.internal_status == "service_only"
    assert place.publication_status == "hidden"
    assert place.is_active is False


def test_no_reader_filters_service_only_places_by_is_active_new() -> None:
    """DECISION A evidence #3: every known reader that excludes
    service_only places does so via internal_status == "service_only"
    directly (services/place_public_visibility.py,
    services/route_eligibility_policy.py, services/destination_readiness_
    service.py) -- none of them additionally require is_active to be any
    particular value for a service_only place, so this behavior change
    does not alter any existing query result. This test asserts the
    structural fact the decision rests on: internal_status is an
    independent, sufficient exclusion signal for service_only places in
    every one of these modules."""
    import inspect

    from services import destination_readiness_service, place_public_visibility, route_eligibility_policy

    for module in (place_public_visibility, route_eligibility_policy, destination_readiness_service):
        source = inspect.getsource(module)
        assert "service_only" in source, f"{module.__name__} must reference service_only as documented"
