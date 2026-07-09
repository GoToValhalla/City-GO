from __future__ import annotations

import pytest


_DISABLED_ENDPOINTS: list[tuple[str, str, dict[str, object] | None, str]] = [
    ("GET", "/me", None, "profile.enabled"),
    ("PATCH", "/me/profile", {"display_name": "Test"}, "profile.enabled"),
    ("POST", "/identity/telegram/verify", {"init_data": "unsafe-placeholder"}, "telegram_identity.enabled"),
    (
        "POST",
        "/identity/link",
        {
            "from_identity_type": "anonymous",
            "from_identity_id": "anonymous-id",
            "to_identity_type": "telegram",
            "to_identity_id": "telegram-id",
            "method": "telegram_init_data",
        },
        "account_linking.enabled",
    ),
    ("GET", "/identity/links", None, "account_linking.enabled"),
    ("GET", "/me/favorites", None, "favorites.enabled"),
    ("POST", "/me/favorites/places/1", {"anonymous_device_id": "device"}, "favorites.enabled"),
    ("DELETE", "/me/favorites/places/1", None, "favorites.enabled"),
    ("GET", "/me/saved-routes", None, "saved_routes.enabled"),
    ("POST", "/me/saved-routes", {"title": "Draft", "route_snapshot_json": {"points": []}}, "saved_routes.enabled"),
    ("GET", "/places/1/reviews", None, "public_reviews.enabled"),
    ("POST", "/places/1/reviews", {"rating": 5, "text": "Good"}, "reviews.enabled"),
    ("POST", "/reviews/review-id/vote", {"value": 1}, "review_votes.enabled"),
    (
        "POST",
        "/places/1/suggestions",
        {"kind": "report_problem", "payload_json": {"text": "wrong hours"}},
        "suggestions.enabled",
    ),
    ("GET", "/admin/moderation", None, "moderation.enabled"),
    ("POST", "/admin/moderation/item-id/approve", {"reason": "ok"}, "moderation.enabled"),
    ("POST", "/admin/moderation/item-id/reject", {"reason": "spam"}, "moderation.enabled"),
]


@pytest.mark.parametrize(("method", "path", "payload", "feature"), _DISABLED_ENDPOINTS)
def test_new_user_foundation_endpoints_return_404_when_flags_off_new(client, method: str, path: str, payload: dict[str, object] | None, feature: str) -> None:
    response = client.request(method, path, json=payload)

    assert response.status_code == 404
    assert response.json() == {"detail": {"code": "feature_disabled", "feature": feature}}


def test_existing_public_cities_endpoint_does_not_require_auth_new(client) -> None:
    response = client.get("/cities/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_no_reviews_leak_when_public_reviews_flag_off_new(client) -> None:
    response = client.get("/places/1/reviews")
    assert response.status_code == 404
    assert response.json() == {"detail": {"code": "feature_disabled", "feature": "public_reviews.enabled"}}


def test_dark_launch_endpoints_hidden_from_openapi_new(client) -> None:
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]

    hidden_paths = [
        "/me",
        "/me/profile",
        "/identity/telegram/verify",
        "/identity/link",
        "/identity/links",
        "/me/favorites",
        "/me/saved-routes",
        "/places/{place_id}/reviews",
        "/reviews/{review_id}/vote",
        "/places/{place_id}/suggestions",
        "/admin/moderation",
    ]
    for path in hidden_paths:
        assert path not in paths, f"{path} must not be present in OpenAPI schema while flags are OFF"


def test_place_detail_route_not_shadowed_by_reviews_route_new(client, place_factory) -> None:
    place = place_factory()

    detail_response = client.get(f"/places/{place.id}")
    assert detail_response.status_code == 200

    reviews_response = client.get(f"/places/{place.id}/reviews")
    assert reviews_response.status_code == 404
    assert reviews_response.json() == {"detail": {"code": "feature_disabled", "feature": "public_reviews.enabled"}}
