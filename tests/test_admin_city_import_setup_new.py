from datetime import datetime

from models.city import City
from models.city_import_scope import CityImportScope
from schemas.admin import AdminCityCreateRequest
from services.admin_city_bbox import bbox_from_center_radius
from services.admin_city_import_setup import finish_city_import_setup


def test_bbox_from_center_radius_new() -> None:
    bbox = bbox_from_center_radius(43.24, 76.95, 15)
    assert bbox["south"] < 43.24 < bbox["north"]
    assert bbox["west"] < 76.95 < bbox["east"]


def test_finish_city_import_setup_creates_scopes_new(db_session, monkeypatch) -> None:
    monkeypatch.setattr(
        "services.admin_city_import_setup.geocode_city_name",
        lambda **_: type("Geo", (), {"lat": 43.24, "lng": 76.95, "display_name": "Almaty"})(),
    )
    city = City(name="Алматы", slug="almaty-test", country="Казахстан", launch_status="importing", is_active=False)
    db_session.add(city)
    db_session.flush()
    payload = AdminCityCreateRequest(name="Алматы", country="Казахстан", region="Алматы", radius_km=12)
    finish_city_import_setup(db_session, city, payload, now=datetime(2026, 6, 8, 12, 0, 0))
    db_session.commit()
    scopes = db_session.query(CityImportScope).filter_by(city_id=city.id).all()
    assert len(scopes) == 3
    assert city.center_lat == 43.24
    assert city.bbox == bbox_from_center_radius(43.24, 76.95, 12)
    assert all(scope.enabled for scope in scopes)
