from datetime import datetime
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from main import app
from schemas.user_signal import UserDerivedProfile, UserSignalSummary


def test_user_signal_summary_endpoint_returns_counts() -> None:
    summary = UserSignalSummary(
        user_id="u1",
        total=1,
        by_signal_type={"view_place": 1},
        by_entity_type={"place": 1},
    )
    with patch("routers.user_signals.summarize_user_signals", return_value=summary):
        response = TestClient(app).get("/user-signals/u1/summary")
    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_user_signal_create_endpoint_returns_signal() -> None:
    signal = MagicMock()
    signal.id = 1
    signal.user_id = "u1"
    signal.signal_type = "view_place"
    signal.entity_type = "place"
    signal.entity_id = "p1"
    signal.payload = None
    signal.created_at = datetime(2030, 1, 1)
    with patch("routers.user_signals.create_user_signal", return_value=signal):
        response = TestClient(app).post(
            "/user-signals/",
            json={"user_id": "u1", "signal_type": "view_place", "entity_type": "place", "entity_id": "p1"},
        )
    assert response.status_code == 200
    assert response.json()["signal_type"] == "view_place"


def test_user_derived_profile_endpoint_returns_profile() -> None:
    profile = UserDerivedProfile(
        user_id="u1",
        total_signals=1,
        preferred_categories={"coffee": 1},
        action_counts={"view_place": 1},
    )
    with patch("routers.user_signals.derive_user_profile", return_value=profile):
        response = TestClient(app).get("/user-signals/u1/profile")
    assert response.status_code == 200
    assert response.json()["preferred_categories"] == {"coffee": 1}
