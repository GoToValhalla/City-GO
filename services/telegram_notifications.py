"""Shared Telegram notifications for operational admin actions."""
from __future__ import annotations

import httpx

from core.config import settings


def send_telegram_notification(text: str) -> bool:
    """Send a plain-text message to the same operational Telegram chat used by CI/deploy/monitoring."""
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return False
    try:
        response = httpx.post(
            f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
            json={"chat_id": settings.telegram_chat_id, "text": text},
            timeout=8,
        )
        return response.status_code < 400
    except httpx.HTTPError:
        return False
