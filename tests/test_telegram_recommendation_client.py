import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from telegram_bot.services.recommendation_client import RecommendationApiClient


def test_build_route_disables_environment_proxy() -> None:
    response = MagicMock()
    response.json.return_value = {"route_id": "r1", "points": []}
    client = AsyncMock()
    client.post.return_value = response

    with patch("telegram_bot.services.recommendation_client.httpx.AsyncClient") as factory:
        factory.return_value.__aenter__.return_value = client
        result = asyncio.run(RecommendationApiClient().build_route(1.0, 2.0))

    assert result["ok"] is True
    assert factory.call_args.kwargs["trust_env"] is False


def test_build_route_sends_user_intent_payload() -> None:
    response = MagicMock()
    response.json.return_value = {"route_id": "r1", "points": []}
    client = AsyncMock()
    client.post.return_value = response

    with patch("telegram_bot.services.recommendation_client.httpx.AsyncClient") as factory:
        factory.return_value.__aenter__.return_value = client
        asyncio.run(
            RecommendationApiClient().build_route(
                1.0,
                2.0,
                minutes=90,
                interests=("cafe",),
                avoided_categories=("museum",),
            )
        )

    payload = client.post.call_args.kwargs["json"]
    assert payload["time_budget_minutes"] == 90
    assert payload["interests"] == ["cafe"]
    assert payload["avoided_categories"] == ["museum"]


def test_correct_route_sends_text_correction_payload() -> None:
    response = MagicMock()
    response.json.return_value = {"route_id": "r1", "points": []}
    client = AsyncMock()
    client.post.return_value = response

    with patch("telegram_bot.services.recommendation_client.httpx.AsyncClient") as factory:
        factory.return_value.__aenter__.return_value = client
        asyncio.run(
            RecommendationApiClient().correct_route(
                {"route_id": "r1"},
                "avoid_category",
                avoided_categories=["museum"],
            )
        )

    payload = client.post.call_args.kwargs["json"]
    assert payload["action"] == "avoid_category"
    assert payload["avoided_categories"] == ["museum"]
