from fastapi.testclient import TestClient

from core.config import settings
from main import app

_TOKEN = "test-place-seed-admin-token"
_HEADERS = {"Authorization": f"Bearer {_TOKEN}"}


def test_validate_place_seed_payload_returns_empty_bulk_result_for_empty_list(monkeypatch) -> None:
    monkeypatch.setattr(settings, "admin_api_token", _TOKEN)
    client = TestClient(app)

    response = client.post(
        "/place-seed/validate/",
        headers=_HEADERS,
        json={"items": []},
    )

    assert response.status_code == 200
    assert response.json() == {
        "total": 0,
        "valid_count": 0,
        "invalid_count": 0,
        "items": [],
    }