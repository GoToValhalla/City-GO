import pytest
from sqlalchemy.orm import Session

from services.admin_city_publication_service import publish_city
from services.place_service import get_places


def test_publish_city_publishes_only_public_safe_places_new(db_session: Session, city_factory, place_factory) -> None:
    city = city_factory(slug="review-city", name="Review City", is_active=False, launch_status="review_required")
    cafe = place_factory(city_id=city.id, slug="review-cafe", title="Review Cafe", category="cafe")
    pharmacy = place_factory(city_id=city.id, slug="review-pharmacy", title="Review Pharmacy", category="health")

    result = publish_city(db_session, city.id, actor="test-admin")

    assert result is not None
    assert result.city.launch_status == "published"
    assert result.city.is_active is True
    assert result.places_total == 2
    assert result.places_published == 1
    assert result.places_hidden == 1

    db_session.refresh(cafe)
    db_session.refresh(pharmacy)
    assert cafe.is_published is True
    assert cafe.is_visible_in_catalog is True
    assert cafe.is_route_eligible is True
    assert pharmacy.is_published is False
    assert pharmacy.is_visible_in_catalog is False
    assert pharmacy.is_route_eligible is False


def test_publish_city_requires_at_least_one_public_place_new(db_session: Session, city_factory, place_factory) -> None:
    city = city_factory(slug="empty-public-city", name="Empty Public City", is_active=False, launch_status="review_required")
    place_factory(city_id=city.id, slug="only-pharmacy", title="Only Pharmacy", category="health")

    with pytest.raises(ValueError):
        publish_city(db_session, city.id, actor="test-admin")

    db_session.refresh(city)
    assert city.launch_status == "review_required"
    assert city.is_active is False


def test_public_places_require_published_city_new(db_session: Session, city_factory, place_factory) -> None:
    city = city_factory(slug="hidden-city", name="Hidden City", is_active=False, launch_status="review_required")
    place = place_factory(city_id=city.id, slug="hidden-cafe", title="Hidden Cafe", category="cafe")
    place.is_published = True
    place.is_visible_in_catalog = True
    place.is_searchable = True
    place.is_route_eligible = True
    db_session.commit()

    assert get_places(db_session, city_slug=city.slug) == []

    publish_city(db_session, city.id, actor="test-admin")

    visible = get_places(db_session, city_slug=city.slug)
    assert [item.slug for item in visible] == ["hidden-cafe"]
