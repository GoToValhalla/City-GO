from fastapi.testclient import TestClient

from main import app


def test_dry_run_place_seed_payload_returns_empty_summary_for_empty_list() -> None:
    client = TestClient(app)

    response = client.post(
        "/place-seed/dry-run/",
        json={"items": []},
    )

    assert response.status_code == 200
    assert response.json() == {
        "total": 0,
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "invalid": 0,
        "errors": [],
        "auto_published": 0,
        "needs_review_count": 0,
        "rejected_count": 0,
    }
