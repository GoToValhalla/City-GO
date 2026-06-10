"""Тесты режима перепроверки существующих адресов."""

from __future__ import annotations


def test_address_verify_existing_marks_matching_address_new(db_session, monkeypatch) -> None:
    from models.city import City
    from models.place import Place
    from services.place_address_backfill import run_backfill

    city = City(name="T", slug="addr-verify", country="KZ", launch_status="imported", is_active=True)
    db_session.add(city)
    db_session.flush()
    place = Place(
        city_id=city.id,
        slug="p2",
        title="Cafe 2",
        category="food",
        lat=43.24,
        lng=76.95,
        address="улица Абая, 10",
    )
    db_session.add(place)
    db_session.commit()
    place_id = place.id

    monkeypatch.setattr("services.place_address_backfill.reverse_geocode", lambda lat, lng: "Абая 10, Алматы")
    monkeypatch.setattr("services.place_address_backfill.should_apply_geocode_result", lambda c, cat: True)
    stats = run_backfill(
        db_session,
        city_slug="addr-verify",
        limit=10,
        sleep_seconds=0,
        apply=True,
        verify_existing=True,
    )
    updated_place = db_session.get(Place, place_id)

    assert stats["verified_existing"] == 1
    assert stats["sent_to_review"] == 0
    assert updated_place is not None
    assert updated_place.address == "улица Абая, 10"
    assert updated_place.address_confidence == 0.75
    assert updated_place.address_updated_at is not None


def test_address_verify_existing_sends_conflict_to_review_new(db_session, monkeypatch) -> None:
    from models.city import City
    from models.place import Place
    from services.place_address_backfill import run_backfill

    city = City(name="T", slug="addr-conflict", country="KZ", launch_status="imported", is_active=True)
    db_session.add(city)
    db_session.flush()
    place = Place(
        city_id=city.id,
        slug="p3",
        title="Cafe 3",
        category="food",
        lat=43.24,
        lng=76.95,
        address="улица Абая, 10",
    )
    db_session.add(place)
    db_session.commit()
    place_id = place.id

    monkeypatch.setattr("services.place_address_backfill.reverse_geocode", lambda lat, lng: "проспект Достык 99, Алматы")
    monkeypatch.setattr("services.place_address_backfill.should_apply_geocode_result", lambda c, cat: True)
    stats = run_backfill(
        db_session,
        city_slug="addr-conflict",
        limit=10,
        sleep_seconds=0,
        apply=True,
        verify_existing=True,
    )
    updated_place = db_session.get(Place, place_id)

    assert stats["verified_existing"] == 0
    assert stats["sent_to_review"] == 1
    assert updated_place is not None
    assert updated_place.address == "улица Абая, 10"
    assert updated_place.verification_status == "needs_recheck"
    assert updated_place.verification_method == "address_conflict"
    assert "Достык" in str(updated_place.verification_comment)
