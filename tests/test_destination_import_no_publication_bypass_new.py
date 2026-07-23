"""Destination import must construct new places with no publication state
set, and let the canonical publication writer be the only thing that
publishes/hides them -- it must never construct an already-"published"
Place directly (the confirmed bypass this fix removes). The end state
(published for ordinary categories, hidden for service_only ones) is
unchanged; only how it is reached changes: via an audited
transition_place_publication call instead of raw constructor kwargs."""

from __future__ import annotations

from models.place import Place
from models.place_publication_transition import PlacePublicationTransition
from services.destination_candidate_adapter import DestinationCandidate
from services.destination_import_service import _upsert_candidate

from tests.destination_pipeline_helpers import destination_with_scope


def _candidate(**overrides) -> DestinationCandidate:
    base = dict(
        slug="curonian-museum",
        title="Морской музей",
        category="museum",
        lat=54.75,
        lng=20.5,
        source="osm_overpass",
        changes={},
    )
    base.update(overrides)
    return DestinationCandidate(**base)


def test_destination_import_creates_place_via_canonical_writer_new(db_session, city_factory) -> None:
    _, dest, scope = destination_with_scope(db_session, city_factory, slug="new-place-draft")
    counters: dict[str, int] = {"places_created": 0, "duplicates_skipped": 0, "memberships_created": 0, "memberships_updated": 0, "service_only_hidden": 0}

    place = _upsert_candidate(db_session, dest.legacy_city_id, dest, scope, _candidate(), counters)
    db_session.commit()
    db_session.refresh(place)

    assert place.publication_status == "published"
    assert place.is_published is True
    assert place.is_visible_in_catalog is True
    assert place.is_route_eligible is True
    assert place.is_searchable is True
    assert place.is_active is True

    transitions = db_session.query(PlacePublicationTransition).filter_by(place_id=place.id).all()
    assert len(transitions) == 1
    transition = transitions[0]
    assert transition.to_status == "published"
    assert transition.actor == "destination_import"
    assert transition.source == "destination_import"


def test_destination_import_service_only_category_is_hidden_via_canonical_writer_new(db_session, city_factory) -> None:
    _, dest, scope = destination_with_scope(db_session, city_factory, slug="new-place-hidden")
    counters: dict[str, int] = {"places_created": 0, "duplicates_skipped": 0, "memberships_created": 0, "memberships_updated": 0, "service_only_hidden": 0}

    place = _upsert_candidate(
        db_session, dest.legacy_city_id, dest, scope,
        _candidate(slug="curonian-pharmacy", title="Аптека", category="pharmacy"),
        counters,
    )
    db_session.commit()
    db_session.refresh(place)

    assert place.publication_status == "hidden"
    assert place.is_published is False
    assert place.is_active is False

    transition = db_session.query(PlacePublicationTransition).filter_by(place_id=place.id).one()
    assert transition.to_status == "hidden"
    assert transition.actor == "destination_import"


def test_destination_import_never_constructs_place_with_controlled_kwargs_new(db_session, city_factory) -> None:
    """Direct regression for the confirmed bypass: the constructed Place
    must reach the database with no controlled publication field set
    until the canonical writer runs -- proven by inspecting the row
    immediately after add()+flush(), before transition_place_publication
    is called, via the same code path the service itself uses."""
    from services.destination_import_service import _new_place

    place = _new_place(city_id=1, candidate=_candidate(), service_only=False)

    assert place.publication_status is None
    assert place.is_published is None
    assert place.is_visible_in_catalog is None
    assert place.is_route_eligible is None
    assert place.is_searchable is None
