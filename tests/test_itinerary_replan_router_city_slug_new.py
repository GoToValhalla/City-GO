"""Regression: legacy replan router must read city_slug from current_route."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from db.dependencies import get_db
from routers.itinerary import router
from schemas.itinerary_replan import ItineraryReplanResponse


def test_replan_router_uses_current_route_city_slug_new() -> None:
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: (yield MagicMock())

    with patch("routers.itinerary.assert_route_generation_allowed") as allowed, patch(
        "routers.itinerary.replan_itinerary",
        return_value=ItineraryReplanResponse(status="ok", title="t", summary="s", points=[]),
    ), patch("routers.itinerary.log_route_generation_started"), patch(
        "routers.itinerary.log_route_generation_failed"
    ):
        response = TestClient(app).post(
            "/routes/replan",
            json={
                "current_route": {
                    "city_slug": "replan-city",
                    "route_mode": "walk",
                    "points": [{"place_id": 1, "position": 1}],
                },
                "reason_type": "shorten_route",
            },
        )

    assert response.status_code == 200
    allowed.assert_called_once()
    assert allowed.call_args.kwargs["city_slug"] == "replan-city"
