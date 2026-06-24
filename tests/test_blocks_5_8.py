"""Тесты блоков 5-8: lookup, категории, address_source, slug."""

from core.place_category_hierarchy import LEGACY_TO_CANONICAL, normalize_category_code
from services.slug_transliterate import transliterate_cyrillic


def test_normalize_category_legacy_new() -> None:
    assert normalize_category_code("cafe") == "coffee"
    assert normalize_category_code("culture") == "museum"
    assert normalize_category_code("food") == "food"


def test_legacy_map_covers_osm_drift_new() -> None:
    assert LEGACY_TO_CANONICAL["useful"] == "service"


def test_transliterate_almaty_slug_new() -> None:
    assert transliterate_cyrillic("Алматы") == "almaty"


def test_address_backfill_sets_source_new(db_session, monkeypatch) -> None:
    from models.city import City
    from models.place import Place
    from services.place_address_backfill import run_backfill

    city = City(name="T", slug="addr-src", country="KZ", launch_status="imported", is_active=True)
    db_session.add(city)
    db_session.flush()
    place = Place(city_id=city.id, slug="p1", title="Cafe", category="food", lat=43.24, lng=76.95, address=None)
    db_session.add(place)
    db_session.commit()
    place_id = place.id

    monkeypatch.setattr("services.place_address_backfill.reverse_geocode", lambda lat, lng: "Test St 1")
    monkeypatch.setattr("services.place_address_backfill.should_apply_geocode_result", lambda c, cat: True)
    stats = run_backfill(db_session, city_slug="addr-src", limit=10, sleep_seconds=0, apply=True)
    updated_place = db_session.get(Place, place_id)

    assert stats["updated"] == 1
    assert updated_place is not None
    assert updated_place.address_source == "nominatim_reverse"
    assert updated_place.address_confidence == 0.75
    assert updated_place.address_updated_at is not None
