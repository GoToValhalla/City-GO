from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from core.admin_auth import AdminContext, admin_required
from main import app
from schemas.place_verification import PlaceVerificationEnqueueSummary


# enqueue-stale теперь требует admin auth — bypass для существующих тестов логики.
@pytest.fixture(autouse=True)
def _bypass_admin_auth():
    app.dependency_overrides[admin_required] = lambda: AdminContext(
        actor_id="test-admin", actor_role="admin", auth_source="test"
    )
    yield
    app.dependency_overrides.pop(admin_required, None)


def test_enqueue_stale_places_endpoint(client) -> None:
    summary = PlaceVerificationEnqueueSummary(city_slug="zelenogradsk", enqueued=2)
    with patch("routers.place_verification.enqueue_stale_places", return_value=summary):
        response = client.post("/place-verification/enqueue-stale/zelenogradsk")
    assert response.status_code == 200
    assert response.json()["enqueued"] == 2


def test_pending_verification_queue_endpoint() -> None:
    with patch("routers.place_verification.pending_verification_tasks", return_value=[]):
        response = TestClient(app).get("/place-verification/queue")
    assert response.status_code == 200
    assert response.json() == []
