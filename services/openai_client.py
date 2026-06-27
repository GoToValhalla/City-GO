"""Small OpenAI HTTP client used by admin-only AI automation."""
from __future__ import annotations

import json
from typing import Any

import httpx

from core.config import settings


class OpenAIClientError(RuntimeError):
    """Raised when OpenAI is not configured or returns an unusable response."""


def request_json_object(
    *,
    messages: list[dict[str, str]],
    model: str | None = None,
    temperature: float = 0.2,
) -> dict[str, Any]:
    if not settings.openai_api_key:
        raise OpenAIClientError("OPENAI_API_KEY is not configured")

    payload: dict[str, Any] = {
        "model": model or settings.openai_model,
        "messages": messages,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=settings.openai_timeout_seconds,
        )
    except httpx.HTTPError as exc:
        raise OpenAIClientError(f"OpenAI request failed: {exc}") from exc

    if response.status_code >= 400:
        body = response.text[:500]
        raise OpenAIClientError(f"OpenAI returned {response.status_code}: {body}")

    try:
        data = response.json()
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise OpenAIClientError("OpenAI response has unexpected shape") from exc

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise OpenAIClientError("OpenAI response is not valid JSON") from exc

    if not isinstance(parsed, dict):
        raise OpenAIClientError("OpenAI JSON response is not an object")
    return parsed
