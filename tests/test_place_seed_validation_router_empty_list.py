from fastapi.testclient import TestClient

from main import app


def test_validate_place_seed_payload_returns_empty_bulk_result_for_empty_list() -> None:
    client = TestClient(app)

    response = client.post(
        "/place-seed/validate/",
        json={"items": []},
    )

    assert response.status_code == 200
    assert response.json() == {
        "total": 0,
        "valid_count": 0,
        "invalid_count": 0,
        "items": [],
    }