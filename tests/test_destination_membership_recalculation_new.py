from __future__ import annotations

from models.destination import DestinationMembershipConflict, DestinationPlaceMembership, DestinationScope
from tests.destination_pipeline_helpers import destination_with_scope


def test_destination_recalc_assigns_stale_place_new(client, db_session, city_factory, place_factory):
    city, dest, _ = destination_with_scope(db_session, city_factory, slug="recalc-dest")
    place = place_factory(city_id=city.id, slug="inside-recalc", lat=54.75, lng=20.5)
    result = client.post(f"/admin/destinations/{dest.slug}/memberships/recalculate")
    assert result.status_code == 200
    assert db_session.query(DestinationPlaceMembership).filter_by(place_id=place.id, destination_id=dest.id).count() == 1


def test_destination_recalc_preserves_manual_hidden_membership_new(client, db_session, city_factory, place_factory):
    city, dest, _ = destination_with_scope(db_session, city_factory, slug="manual-dest")
    place = place_factory(city_id=city.id, slug="manual-hidden", lat=54.75, lng=20.5)
    row = DestinationPlaceMembership(place_id=place.id, destination_id=dest.id, assignment_type="manual", is_hidden=True)
    db_session.add(row)
    db_session.commit()
    client.post(f"/admin/destinations/{dest.slug}/memberships/recalculate")
    db_session.refresh(row)
    assert row.assignment_type == "manual"
    assert row.is_hidden is True


def test_destination_recalc_overlapping_scope_conflict_new(client, db_session, city_factory, place_factory):
    city, dest, scope = destination_with_scope(db_session, city_factory, slug="overlap-recalc")
    db_session.add(DestinationScope(destination_id=dest.id, code="second", name="Второй", bbox=scope.bbox, enabled=True, priority=scope.priority))
    place = place_factory(city_id=city.id, slug="overlap-place", lat=54.75, lng=20.5)
    db_session.commit()
    client.post(f"/admin/destinations/{dest.slug}/memberships/recalculate")
    assert db_session.query(DestinationMembershipConflict).filter_by(place_id=place.id, destination_id=dest.id).count() == 1
