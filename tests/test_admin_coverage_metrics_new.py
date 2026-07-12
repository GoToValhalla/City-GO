"""Тесты метрик Data Coverage (published scope, strict address/photo policy)."""

from models.city import City
from models.place import Place
from models.place_image import PLACE_IMAGE_STATUS_APPROVED, PlaceImage
from services.admin_coverage_metrics import build_coverage_summary, city_coverage_row


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


def test_coverage_summary_city_with_no_published_places_does_not_raise_new(db_session) -> None:
    """Regression for production 500 (KeyError: 'with_photo'): a city with
    zero published places is absent from _published_quality_by_city's result
    (it only iterates published places), so with_photo/with_addr/with_desc
    must default to 0 from _empty_metrics rather than being missing keys."""
    city = _seed_city(db_session, slug="cov-no-published")
    _seed_place(db_session, city, slug="draft-only", is_published=False, publication_status="draft")
    db_session.commit()

    items, total = build_coverage_summary(db_session)

    assert total >= 1
    row = next(r for r in items if r["city_slug"] == "cov-no-published")
    assert row["places_published"] == 0
    assert row["places_with_photo"] == 0
    assert row["places_without_photo"] == 0
    assert row["places_with_address"] == 0
    assert row["places_with_description"] == 0


def test_coverage_summary_city_with_zero_places_does_not_raise_new(db_session) -> None:
    """A city with no places at all must also produce a complete row, not a
    KeyError from a partially-populated metrics dict."""
    city = _seed_city(db_session, slug="cov-empty-city")
    db_session.commit()

    items, total = build_coverage_summary(db_session)

    row = next(r for r in items if r["city_slug"] == "cov-empty-city")
    assert row["places_total"] == 0
    assert row["places_with_photo"] == 0
    assert row["places_with_address"] == 0
    assert row["places_with_description"] == 0
    assert row["quality_score"] == 0


def test_coverage_summary_api_returns_200_for_city_with_no_published_places_new(client, db_session) -> None:
    city = _seed_city(db_session, slug="cov-api-no-published")
    _seed_place(db_session, city, slug="draft-only-api", is_published=False, publication_status="draft")
    db_session.commit()

    response = client.get("/admin/coverage/summary?limit=5")

    assert response.status_code == 200
    body = response.json()
    row = next(r for r in body["items"] if r["city_slug"] == "cov-api-no-published")
    assert row["places_with_photo"] == 0
    assert row["places_without_photo"] == 0
