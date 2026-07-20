from unittest.mock import patch

from fastapi.testclient import TestClient

from core.config import settings
from main import app
from schemas.place_seed_import_summary import PlaceSeedImportSummary

_TOKEN = "test-place-seed-admin-token"
_HEADERS = {"Authorization": f"Bearer {_TOKEN}"}


def test_place_seed_import_endpoint_returns_summary(monkeypatch) -> None:
    monkeypatch.setattr(settings, "admin_api_token", _TOKEN)
    summary = PlaceSeedImportSummary(total=0)
    with patch("routers.place_seed_import.import_place_seed_items", return_value=summary):
        response = TestClient(app).post(
            "/place-seed/import/",
            headers=_HEADERS,
            json={"items": [], "dry_run": True},
        )
    assert response.status_code == 200
    assert response.json()["total"] == 0


def test_place_coverage_endpoint_returns_report() -> None:
    report = {
        "city_slug": "zelenogradsk",
        "total_places": 0,
        "with_coordinates": 0,
        "with_opening_hours": 0,
        "with_visit_duration": 0,
        "with_source": 0,
        "average_confidence": None,
        "category_counts": {},
        "missing_required_categories": [],
        "route_ready_score": 0.0,
    }
    with patch("routers.place_coverage.build_place_coverage_report", return_value=report):
        response = TestClient(app).get("/place-coverage/zelenogradsk")
    assert response.status_code == 200
    assert response.json()["city_slug"] == "zelenogradsk"
