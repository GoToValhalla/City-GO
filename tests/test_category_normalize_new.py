"""Нормализация категорий города."""

from sqlalchemy import event

from models.category import Category
from models.city import City
from models.place import Place
from services.category_normalize_service import _canonical_category, normalize_city_categories, normalize_places_categories


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


def _count_category_selects(db_session, action) -> int:
    counter = {"n": 0}

    def _before_execute(conn, clauseelement, multiparams, params, execution_options):
        sql = str(clauseelement).lower()
        if "categories" in sql and "select" in sql:
            counter["n"] += 1

    event.listen(db_session.get_bind(), "before_execute", _before_execute)
    try:
        action()
    finally:
        event.remove(db_session.get_bind(), "before_execute", _before_execute)
    return counter["n"]


def test_canonical_category_lookup_is_not_n_plus_1_new(db_session) -> None:
    """Regression: with a shared cache, _canonical_category must issue at most one
    Category SELECT per distinct code across repeated calls, not one per call."""
    cache: dict = {}
    query_count = _count_category_selects(
        db_session,
        lambda: [_canonical_category(db_session, "coffee", apply=True, cache=cache) for _ in range(20)],
    )
    assert query_count <= 1


def test_canonical_category_cache_reuses_created_category_new(db_session) -> None:
    """Behavior-preserving: the same brand-new category code resolves to the
    same Category row across the batch, whether served from cache or re-queried."""
    cache: dict = {}
    first = _canonical_category(db_session, "unique_test_code_123", apply=True, cache=cache)
    second = _canonical_category(db_session, "unique_test_code_123", apply=True, cache=cache)
    assert first is not None
    assert second is not None
    assert first.id == second.id
    assert db_session.query(Category).filter(Category.code == "unique_test_code_123").count() == 1
