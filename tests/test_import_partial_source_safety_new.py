from __future__ import annotations

from data.scripts import import_city_osm_v2 as safe_import
from models.city import City
from models.city_import_scope import CityImportScope
from models.place import Place
from models.place_scope_link import PlaceScopeLink
from models.place_source_presence import PlaceSourcePresence
from services.import_job_service import create_batch
from services.place_import_lifecycle_service import apply_accepted_import_to_place


def _city_scope(db_session):
    city = City(slug="partial-safe-city", name="Partial Safe City", country="Test")
    db_session.add(city)
    db_session.commit()
    scope = CityImportScope(
        city_id=city.id,
        code="core",
        name="Core",
        enabled=True,
        status="enabled",
        import_profile="tourist_core",
    )
    db_session.add(scope)
    db_session.commit()
    return city, scope


def _place(city_id: int, *, slug: str, source_url: str, address: str | None = "Known address") -> Place:
    return Place(
        city_id=city_id,
        slug=slug,
        title=slug,
        category="cafe",
        address=address,
        lat=10.0,
        lng=20.0,
        source="osm",
        source_url=source_url,
        status="active",
        is_active=True,
        is_published=True,
        is_visible_in_catalog=True,
        is_route_eligible=True,
        is_searchable=True,
        publication_status="published",
    )


def _accepted_item(*, address):
    return {
        "title": "Known cafe",
        "category": "cafe",
        "raw_lat": 10.0,
        "raw_lng": 20.0,
        "lifecycle_status": "active",
        "short_description": None,
        "address": address,
        "source_url": "https://www.openstreetmap.org/node/1",
        "opening_hours": None,
        "website": None,
        "phone": None,
    }


def test_existing_address_survives_incoming_null_new():
    place = _place(1, slug="known-cafe", source_url="https://www.openstreetmap.org/node/1")

    apply_accepted_import_to_place(place, _accepted_item(address=None), category_id=1)

    assert place.address == "Known address"


def test_existing_address_survives_incoming_blank_new():
    place = _place(1, slug="known-cafe", source_url="https://www.openstreetmap.org/node/1")

    apply_accepted_import_to_place(place, _accepted_item(address="   "), category_id=1)

    assert place.address == "Known address"


def test_non_lifecycle_rejection_does_not_hide_existing_place_new(db_session):
    city, _scope = _city_scope(db_session)
    place = _place(city.id, slug="keep-place", source_url="https://www.openstreetmap.org/node/7")
    db_session.add(place)
    db_session.commit()

    decision = safe_import._hide_existing_rejected_place_safe(
        db_session,
        city.id,
        {
            "source_url": place.source_url,
            "rejection_reason": "unsupported_category",
        },
    )

    db_session.refresh(place)
    assert decision is None
    assert place.status == "active"
    assert place.is_published is True
    assert place.is_route_eligible is True


def test_explicit_source_closure_can_hide_existing_place_new(db_session):
    city, _scope = _city_scope(db_session)
    place = _place(city.id, slug="closed-place", source_url="https://www.openstreetmap.org/node/8")
    db_session.add(place)
    db_session.commit()

    decision = safe_import._hide_existing_rejected_place_safe(
        db_session,
        city.id,
        {
            "source_url": place.source_url,
            "rejection_reason": "source_closed",
        },
    )

    assert decision is not None
    assert decision.action == "hidden"
    assert place.status == "closed"
    assert place.is_published is False


def test_reconciliation_only_touches_current_profile_new(db_session):
    city, scope = _city_scope(db_session)
    tourist = _place(city.id, slug="tourist", source_url="https://www.openstreetmap.org/node/11")
    food = _place(city.id, slug="food", source_url="https://www.openstreetmap.org/node/12")
    db_session.add_all([tourist, food])
    db_session.commit()
    db_session.add_all(
        [
            PlaceScopeLink(place_id=tourist.id, scope_id=scope.id, relation_type="imported_from_scope"),
            PlaceScopeLink(place_id=food.id, scope_id=scope.id, relation_type="imported_from_scope"),
            PlaceSourcePresence(
                place_id=tourist.id,
                source_type="osm",
                source_profile="tourist_core",
                source_external_id="osm:node:11",
            ),
            PlaceSourcePresence(
                place_id=food.id,
                source_type="osm",
                source_profile="food_and_coffee",
                source_external_id="osm:node:12",
            ),
        ]
    )
    db_session.commit()
    batch = create_batch(db_session, scope, mode="apply")

    token = safe_import._CURRENT_PROFILE.set("tourist_core")
    try:
        result = safe_import._mark_missing_sources_profile_safe(
            db_session,
            scope.id,
            batch.id,
            normalized=[],
            city_admin_import_job_id=None,
        )
    finally:
        safe_import._CURRENT_PROFILE.reset(token)

    tourist_presence = db_session.query(PlaceSourcePresence).filter_by(source_external_id="osm:node:11").one()
    food_presence = db_session.query(PlaceSourcePresence).filter_by(source_external_id="osm:node:12").one()
    assert result["missing_from_source"] == 1
    assert tourist_presence.consecutive_missing_count == 1
    assert food_presence.consecutive_missing_count == 0
    assert food_presence.presence_status == "active_in_source"


def test_legacy_unscoped_presence_is_skipped_fail_closed_new(db_session):
    city, scope = _city_scope(db_session)
    place = _place(city.id, slug="legacy", source_url="https://www.openstreetmap.org/node/13")
    db_session.add(place)
    db_session.commit()
    db_session.add(PlaceScopeLink(place_id=place.id, scope_id=scope.id, relation_type="imported_from_scope"))
    db_session.add(
        PlaceSourcePresence(
            place_id=place.id,
            source_type="osm",
            source_profile=None,
            source_external_id="osm:node:13",
        )
    )
    db_session.commit()
    batch = create_batch(db_session, scope, mode="apply")

    token = safe_import._CURRENT_PROFILE.set("tourist_core")
    try:
        result = safe_import._mark_missing_sources_profile_safe(
            db_session,
            scope.id,
            batch.id,
            normalized=[],
            city_admin_import_job_id=None,
        )
    finally:
        safe_import._CURRENT_PROFILE.reset(token)

    presence = db_session.query(PlaceSourcePresence).filter_by(source_external_id="osm:node:13").one()
    assert result["missing_from_source"] == 0
    assert result["legacy_unscoped_skipped"] == 1
    assert presence.consecutive_missing_count == 0
    assert place.is_published is True


def test_overlapping_osm_object_gets_independent_profile_presence_new(db_session):
    city, _scope = _city_scope(db_session)
    place = _place(city.id, slug="overlap", source_url="https://www.openstreetmap.org/node/14")
    db_session.add(place)
    db_session.commit()

    tourist_token = safe_import._CURRENT_PROFILE.set("tourist_core")
    try:
        safe_import._ensure_source_presence_profile_safe(db_session, place.id, "osm:node:14", None, None)
        db_session.commit()
    finally:
        safe_import._CURRENT_PROFILE.reset(tourist_token)

    food_token = safe_import._CURRENT_PROFILE.set("food_and_coffee")
    try:
        safe_import._ensure_source_presence_profile_safe(db_session, place.id, "osm:node:14", None, None)
        db_session.commit()
    finally:
        safe_import._CURRENT_PROFILE.reset(food_token)

    rows = db_session.query(PlaceSourcePresence).filter_by(source_external_id="osm:node:14").all()
    assert {row.source_profile for row in rows} == {"tourist_core", "food_and_coffee"}
