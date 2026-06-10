"""Тесты фильтров и покрытия админки."""

from models.city import City
from models.place import Place
from services.admin_coverage_metrics import build_coverage_summary
from services.admin_places_filters import apply_place_filters
from services.admin_service import get_admin_places


def _seed_city(db, slug: str = "test-city") -> City:
    city = City(name="Test", slug=slug, country="RU", timezone="UTC", launch_status="published", is_active=True)
    db.add(city)
    db.flush()
    return city


def _seed_place(db, city: City, **kwargs) -> Place:
    defaults = dict(
        city_id=city.id, slug="place-1", title="Кафе", lat=1.0, lng=2.0,
        is_published=True, publication_status="published", image_url=None, address=None,
    )
    defaults.update(kwargs)
    place = Place(**defaults)
    db.add(place)
    db.flush()
    return place


def test_preset_no_photo_new(client, db_session) -> None:
    city = _seed_city(db_session)
    _seed_place(db_session, city, slug="no-photo", image_url=None)
    _seed_place(db_session, city, slug="with-photo", image_url="http://x/img.jpg")
    db_session.commit()
    items, total = get_admin_places(db_session, preset="no_photo")
    assert total == 1
    assert items[0].slug == "no-photo"


def test_coverage_summary_new(client, db_session) -> None:
    city = _seed_city(db_session, slug="cov-city")
    _seed_place(db_session, city, slug="p1", address="ул. Ленина", image_url="http://x/1.jpg", verification_status="verified")
    db_session.commit()
    items, total = build_coverage_summary(db_session)
    assert total >= 1
    row = next(r for r in items if r["city_slug"] == "cov-city")
    assert row["places_total"] == 1
    assert row["quality_score"] >= 0
    assert row["severity"] in ("green", "yellow", "red")


def test_coverage_summary_api_new(client) -> None:
    response = client.get("/admin/coverage/summary")
    assert response.status_code == 200
    body = response.json()
    assert "items" in body
    assert "total" in body
