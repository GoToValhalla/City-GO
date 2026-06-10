"""
Unit tests для models - проверка валидации и constraints.
"""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models.place import Place
from models.city import City
from models.category import Category


@pytest.mark.unit
class TestPlaceModelValidation:
    """Тесты для валидации Place модели."""

    def test_place_creation_required_fields(self, db_session: Session):
        """Создать место с обязательными полями."""
        city = City(
            slug="test-city",
            name="Test City",
            timezone="Europe/Moscow",
            center_lat=55.0,
            center_lng=37.0,
        )
        db_session.add(city)
        db_session.commit()
        
        place = Place(
            city_id=city.id,
            slug="test-place",
            title="Test Place",
            lat=55.0,
            lng=37.0,
        )
        db_session.add(place)
        db_session.commit()
        
        assert place.id is not None
        assert place.is_active is True
        assert place.status == "active"

    def test_place_slug_unique_constraint(self, db_session: Session, city_factory):
        """Slug должен быть уникальным."""
        city = city_factory()
        
        place1 = Place(
            city_id=city.id,
            slug="duplicate-slug",
            title="Place 1",
            lat=55.0,
            lng=37.0,
        )
        db_session.add(place1)
        db_session.commit()
        
        place2 = Place(
            city_id=city.id,
            slug="duplicate-slug",  # Same slug
            title="Place 2",
            lat=55.1,
            lng=37.1,
        )
        db_session.add(place2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()

    def test_place_coordinates_stored_as_float(self, db_session: Session, city_factory):
        """Координаты должны храниться как float."""
        city = city_factory()
        
        place = Place(
            city_id=city.id,
            slug="geo-place",
            title="Geo Place",
            lat=54.96115,
            lng=20.47033,
        )
        db_session.add(place)
        db_session.commit()
        
        assert isinstance(place.lat, float)
        assert isinstance(place.lng, float)
        assert place.lat == 54.96115
        assert place.lng == 20.47033

    def test_place_optional_fields_null(self, db_session: Session, city_factory):
        """Опциональные поля могут быть NULL."""
        city = city_factory()
        
        place = Place(
            city_id=city.id,
            slug="minimal-place",
            title="Minimal Place",
            lat=55.0,
            lng=37.0,
            # Все опциональные поля не заполнены
        )
        db_session.add(place)
        db_session.commit()
        
        assert place.price_level is None
        assert place.short_description is None
        assert place.image_url is None
        assert place.address is None

    def test_place_boolean_defaults(self, db_session: Session, city_factory):
        """Булевы поля должны иметь значения по умолчанию False."""
        city = city_factory()
        
        place = Place(
            city_id=city.id,
            slug="bool-place",
            title="Bool Place",
            lat=55.0,
            lng=37.0,
        )
        db_session.add(place)
        db_session.commit()
        
        assert place.dog_friendly is False
        assert place.family_friendly is False
        assert place.indoor is False
        assert place.outdoor is False

    def test_place_status_default(self, db_session: Session, city_factory):
        """Status должен быть 'active' по умолчанию."""
        city = city_factory()
        
        place = Place(
            city_id=city.id,
            slug="status-place",
            title="Status Place",
            lat=55.0,
            lng=37.0,
        )
        db_session.add(place)
        db_session.commit()
        
        assert place.status == "active"

    def test_place_timestamps(self, db_session: Session, city_factory):
        """Timestamps created_at и updated_at должны быть установлены."""
        city = city_factory()
        
        place = Place(
            city_id=city.id,
            slug="time-place",
            title="Time Place",
            lat=55.0,
            lng=37.0,
        )
        db_session.add(place)
        db_session.commit()
        
        assert place.created_at is not None
        assert place.updated_at is not None
        assert place.created_at == place.updated_at


@pytest.mark.unit
class TestCityModelValidation:
    """Тесты для валидации City модели."""

    def test_city_creation(self, db_session: Session):
        """Создать город с обязательными полями."""
        city = City(
            slug="moscow",
            name="Moscow",
            timezone="Europe/Moscow",
            center_lat=55.7558,
            center_lng=37.6173,
        )
        db_session.add(city)
        db_session.commit()
        
        assert city.id is not None
        assert city.slug == "moscow"
        assert city.name == "Moscow"
        assert city.is_active is True

    def test_city_slug_unique(self, db_session: Session):
        """Slug города должен быть уникальным."""
        city1 = City(
            slug="duplicate",
            name="City 1",
            timezone="Europe/Moscow",
            center_lat=55.0,
            center_lng=37.0,
        )
        db_session.add(city1)
        db_session.commit()
        
        city2 = City(
            slug="duplicate",
            name="City 2",
            timezone="Europe/London",
            center_lat=51.5074,
            center_lng=-0.1278,
        )
        db_session.add(city2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()


@pytest.mark.unit
class TestCategoryModelValidation:
    """Тесты для валидации Category модели."""

    def test_category_creation(self, db_session: Session):
        """Создать категорию."""
        category = Category(
            code="cafe",
            name="Cafe",
        )
        db_session.add(category)
        db_session.commit()
        
        assert category.id is not None
        assert category.code == "cafe"
        assert category.name == "Cafe"
        assert category.is_active is True

    def test_category_code_unique(self, db_session: Session):
        """Code категории должен быть уникальным."""
        cat1 = Category(code="restaurant", name="Restaurant")
        db_session.add(cat1)
        db_session.commit()
        
        cat2 = Category(code="restaurant", name="Food Place")
        db_session.add(cat2)
        
        with pytest.raises(IntegrityError):
            db_session.commit()
