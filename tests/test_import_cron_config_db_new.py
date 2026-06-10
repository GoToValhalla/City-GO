from datetime import datetime

from data.scripts.import_cron_config import load_db_targets, merge_import_targets
from models.city import City
from models.city_import_scope import CityImportScope


def test_merge_import_targets_dedup_new() -> None:
    a = [{"city": "a", "scope": "tourist_core", "profile": "tourist_core", "bbox": {}, "refresh_interval_hours": 168}]
    b = [{"city": "a", "scope": "tourist_core", "profile": "tourist_core", "bbox": {}, "refresh_interval_hours": 168},
         {"city": "a", "scope": "food_area", "profile": "food_and_coffee", "bbox": {}, "refresh_interval_hours": 168}]
    merged = merge_import_targets(a, b)
    assert len(merged) == 2


def test_load_db_targets_from_enabled_scopes_new(db_session) -> None:
    city = City(name="Smoke City", slug="smoke-city-db", country="Россия", launch_status="importing", is_active=False)
    db_session.add(city)
    db_session.flush()
    db_session.add(CityImportScope(
        city_id=city.id, code="tourist_core", name="Tourist", bbox={"south": 1, "west": 2, "north": 3, "east": 4},
        enabled=True, status="enabled", import_profile="tourist_core", next_run_at=datetime.utcnow(),
    ))
    db_session.commit()
    targets = load_db_targets(db_session)
    assert any(t["city"] == "smoke-city-db" and t["scope"] == "tourist_core" for t in targets)
