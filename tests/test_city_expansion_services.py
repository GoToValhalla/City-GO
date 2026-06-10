from datetime import datetime, timedelta

from models.city import City
from models.place import Place
from schemas.city_expansion import CountryCreate, ImportScopeCreate, RegionCreate
from schemas.place_discovery import PlaceDiscoveryCreate
from services.city_registry_service import create_country, create_import_scope, create_region
from services.city_service import get_available_cities
from services.import_job_service import create_batch, due_scopes, lock_scope
from services.import_state_service import update_import_state
from services.place_discovery_service import create_discovery_request


def test_registry_and_available_cities(db_session):
    country = create_country(db_session, CountryCreate(code="GE", name="Грузия"))
    region = create_region(db_session, RegionCreate(country_id=country.id, code="imereti", name="Имерети"))
    db_session.add(City(slug="kutaisi", name="Кутаиси", country_id=country.id, region_id=region.id,
                        country="Грузия", launch_status="draft"))
    db_session.add(City(slug="zelenogradsk", name="Зеленоградск", country="Россия", launch_status="published"))
    db_session.commit()
    assert [city["slug"] for city in get_available_cities(db_session)] == ["zelenogradsk"]
    assert {city["slug"] for city in get_available_cities(db_session, include_draft=True)} == {"kutaisi", "zelenogradsk"}


def test_due_scope_lock_batch_and_state(db_session):
    city = City(slug="zelenogradsk", name="Зеленоградск", country="Россия", launch_status="published")
    db_session.add(city)
    db_session.commit()
    scope = create_import_scope(db_session, ImportScopeCreate(
        city_id=city.id, code="center", name="Центр", enabled=True, status="enabled",
    ))
    scope.next_run_at = datetime.utcnow() - timedelta(hours=1)
    db_session.commit()
    assert due_scopes(db_session, datetime.utcnow())[0].id == scope.id
    assert lock_scope(db_session, scope, datetime.utcnow()) is True
    batch = create_batch(db_session, scope, mode="apply")
    batch.published_count = 1
    state = update_import_state(db_session, batch, "success")
    assert state.coverage_status == "published"


def test_discovery_request_never_publishes_place(db_session):
    city = City(slug="zelenogradsk", name="Зеленоградск", country="Россия")
    db_session.add(city)
    db_session.commit()
    item = create_discovery_request(db_session, PlaceDiscoveryCreate(city_slug="zelenogradsk", name="Кафе X"))
    assert item.status == "new"
    assert db_session.query(Place).count() == 0
