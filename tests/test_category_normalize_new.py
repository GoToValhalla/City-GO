"""Нормализация категорий города."""

from models.city import City
from models.place import Place
from services.category_normalize_service import normalize_city_categories


def test_normalize_city_categories_apply_new(db_session) -> None:
    city = City(name="T", slug="cat-norm", country="KZ", launch_status="imported", is_active=True)
    db_session.add(city)
    db_session.flush()
    db_session.add(Place(city_id=city.id, slug="p1", title="A", category="cafe", lat=1, lng=2))
    db_session.add(Place(city_id=city.id, slug="p2", title="B", category="food", lat=1, lng=2))
    db_session.commit()
    result = normalize_city_categories(db_session, city_slug="cat-norm", apply=True)
    assert result["updated"] == 1
    p1 = db_session.query(Place).filter_by(slug="p1").first()
    assert p1 is not None
    assert p1.category == "coffee"
