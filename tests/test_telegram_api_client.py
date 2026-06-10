import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from telegram_bot.services.api_client import CityGoApiClient


def _mock_get() -> tuple[MagicMock, AsyncMock]:
    response = MagicMock()
    response.json.return_value = []
    client = AsyncMock()
    client.get.return_value = response
    return response, client


def test_nearby_disables_environment_proxy() -> None:
    _response, client = _mock_get()

    with patch("telegram_bot.services.citygo_api_requests.httpx.AsyncClient") as factory:
        factory.return_value.__aenter__.return_value = client
        result = asyncio.run(CityGoApiClient().get_nearby_places(1.0, 2.0))

    assert result["ok"] is True
    assert factory.call_args.kwargs["trust_env"] is False
    assert client.get.call_args.kwargs["params"]["lat"] == 1.0


def test_coffee_uses_requested_city_slug() -> None:
    _response, client = _mock_get()

    with patch("telegram_bot.services.citygo_api_requests.httpx.AsyncClient") as factory:
        factory.return_value.__aenter__.return_value = client
        result = asyncio.run(CityGoApiClient().get_coffee_places("zelenogradsk"))

    assert result["ok"] is True
    assert client.get.call_args.kwargs["params"]["city_slug"] == "zelenogradsk"
