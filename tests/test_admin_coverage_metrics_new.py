"""Тесты метрик Data Coverage (published scope, strict address/photo policy)."""

from models.city import City
from models.place import Place
from models.place_image import PLACE_IMAGE_STATUS_APPROVED, PlaceImage
from services.admin_coverage_metrics import city_coverage_row


def _seed_city(db, slug: str = "cov-metrics") -> City:
    city = City(name="Cov", slug=slug, country="RU", timezone="UTC", launch_status="published", is_active=True)
    db.add(city)
    db.flush()
    return city


def _seed_place(db, city: City, **kwargs) -> Place:
    defaults = dict(
        city_id=city.id,
        slug="place-default",
        title="Place",
        lat=1.0,
        lng=2.0,
        is_published=True,
        publication_status="published",
        image_url=None,
        address=None,
        short_description=None,
    )
    defaults.update(kwargs)
    place = Place(**defaults)
    db.add(place)
    db.flush()
    return place


def test_coverage_published_real_address_not_without_new(db_session) -> None:
    city = _seed_city(db_session, slug="addr-real")
    _seed_place(db_session, city, slug="pub-real", address="ул. Абая, 10", category="cafe")
    db_session.commit()
    row = city_coverage_row(db_session, city)
    assert row["places_without_address"] == 0
    assert row["places_with_address"] == 1


def test_coverage_published_placeholder_counts_without_new(db_session) -> None:
    city = _seed_city(db_session, slug="addr-placeholder")
    _seed_place(db_session, city, slug="pub-ph", address="Адрес не указан", category="cafe")
    db_session.commit()
    row = city_coverage_row(db_session, city)
    assert row["places_without_address"] == 1
    assert row["places_with_address"] == 0


def test_coverage_draft_without_address_ignored_new(db_session) -> None:
    city = _seed_city(db_session, slug="addr-draft")
    _seed_place(
        db_session,
        city,
        slug="draft-no-addr",
        is_published=False,
        publication_status="draft",
        address=None,
    )
    _seed_place(db_session, city, slug="pub-ok", address="ул. Ленина, 1", category="museum")
    db_session.commit()
    row = city_coverage_row(db_session, city)
    assert row["places_published"] == 1
    assert row["places_without_address"] == 0


def test_coverage_approved_place_image_counts_as_photo_new(db_session) -> None:
    city = _seed_city(db_session, slug="photo-approved")
    place = _seed_place(db_session, city, slug="pub-img", image_url=None)
    db_session.add(
        PlaceImage(
            place_id=place.id,
            image_url="https://example.com/a.jpg",
            source_type="manual",
            status=PLACE_IMAGE_STATUS_APPROVED,
            is_primary=True,
        )
    )
    db_session.commit()
    row = city_coverage_row(db_session, city)
    assert row["places_without_photo"] == 0
    assert row["places_with_photo"] == 1


def test_coverage_published_without_photo_new(db_session) -> None:
    city = _seed_city(db_session, slug="photo-missing")
    _seed_place(db_session, city, slug="pub-no-img", image_url=None)
    db_session.commit()
    row = city_coverage_row(db_session, city)
    assert row["places_without_photo"] == 1
    assert row["places_with_photo"] == 0


def test_coverage_old_formula_regression_new(db_session) -> None:
    """published=1 без адреса + 2 draft с адресом → without_address=1, не 0."""
    city = _seed_city(db_session, slug="addr-regression")
    _seed_place(
        db_session,
        city,
        slug="pub-no-addr",
        is_published=True,
        address=None,
    )
    _seed_place(
        db_session,
        city,
        slug="draft-1",
        is_published=False,
        address="ул. Одна, 1",
    )
    _seed_place(
        db_session,
        city,
        slug="draft-2",
        is_published=False,
        address="ул. Две, 2",
    )
    db_session.commit()
    row = city_coverage_row(db_session, city)
    assert row["places_published"] == 1
    assert row["places_without_address"] == 1
    assert row["places_with_address"] == 0
