from datetime import datetime

from data.scripts import import_cron_db
from data.scripts.city_coverage_report import parse_args as coverage_args
from data.scripts.import_city_osm import _apply_import, _normalize_osm_object, parse_args as import_args
from data.scripts.import_cron_config import load_targets, select_targets, split_csv
from data.scripts.run_due_import_jobs import parse_args as cron_args
from models.city import City
from models.city_import_scope import CityImportScope
from models.place import Place
from models.place_scope_link import PlaceScopeLink
from models.place_source_presence import PlaceSourcePresence
from services.import_profiles import import_profile_tags, production_profile


class _SessionContext:
    def __init__(self, session):
        self.session = session

    def __enter__(self):
        return self.session

    def __exit__(self, exc_type, exc, traceback):
        return False


def test_import_city_osm_accepts_city_scope_profile_and_dry_run():
    args = import_args(["--city", "kutaisi", "--scope", "tourist_core", "--profile", "tourist_core", "--dry-run"])
    assert (args.city, args.scope, args.profile, args.dry_run) == ("kutaisi", "tourist_core", "tourist_core", True)


def test_city_coverage_report_accepts_scope():
    args = coverage_args(["--city", "yerevan", "--scope", "center"])
    assert (args.city, args.scope) == ("yerevan", "center")


def test_full_osm_is_not_production_profile():
    assert import_profile_tags("full_osm") == ("debug_only",)
    assert production_profile("full_osm") is False


def test_cron_import_args_accept_city_scope_and_apply():
    args = cron_args(["--city", "kutaisi,yerevan", "--scope", "tourist_core", "--apply"])
    assert split_csv(args.city) == ("kutaisi", "yerevan")
    assert split_csv(args.scope) == ("tourist_core",)
    assert args.apply is True


def test_import_target_config_contains_only_planned_cities():
    targets = load_targets()
    cities = {target["city"] for target in targets}
    selected = select_targets(targets, ("khanty-mansiysk",), ())
    assert cities == {"zelenogradsk", "kutaisi", "yerevan", "khanty-mansiysk", "rostov-on-don"}
    assert {target["city"] for target in selected} == {"khanty-mansiysk"}


def test_apply_import_marks_scope_sources_missing(db_session):
    city = City(slug="zelenogradsk", name="Зеленоградск", country="Россия")
    db_session.add(city)
    db_session.commit()
    scope = CityImportScope(city_id=city.id, code="tourist_core", name="Core", enabled=True, status="enabled")
    db_session.add(scope)
    db_session.commit()
    old_place = Place(city_id=city.id, slug="old", title="Old", lat=54.95, lng=20.48)
    db_session.add(old_place)
    db_session.commit()
    db_session.add(PlaceScopeLink(place_id=old_place.id, scope_id=scope.id, relation_type="imported_from_scope"))
    db_session.add(PlaceSourcePresence(place_id=old_place.id, source_type="osm", source_external_id="osm:node:old"))
    db_session.commit()

    raw = [{"type": "node", "id": 1, "lat": 54.96, "lon": 20.49, "tags": {"name": "Кофе", "amenity": "cafe"}}]
    result = _apply_import(db_session, city, scope, "tourist_core", raw, [_normalize_osm_object(raw[0], city.slug)])
    missing = db_session.query(PlaceSourcePresence).filter_by(source_external_id="osm:node:old").first()

    assert result["missing_from_source"] == 1
    assert missing.presence_status == "missing_once"


def test_cron_lock_keeps_paused_scope_paused(db_session, monkeypatch):
    city = City(slug="kutaisi", name="Кутаиси", country="Грузия")
    db_session.add(city)
    db_session.commit()
    scope = CityImportScope(city_id=city.id, code="tourist_core", name="Core", enabled=True, status="paused")
    db_session.add(scope)
    db_session.commit()
    monkeypatch.setattr(import_cron_db, "SessionLocal", lambda: _SessionContext(db_session))

    result = import_cron_db.lock_target(
        {"city": "kutaisi", "scope": "tourist_core", "profile": "tourist_core", "bbox": {}, "refresh_interval_hours": 168},
        datetime.utcnow(),
        True,
    )

    assert result == {"status": "skipped", "reason": "scope_disabled"}
    assert scope.status == "paused"
