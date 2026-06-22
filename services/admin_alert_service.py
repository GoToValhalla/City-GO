"""Runtime admin alerts for import/enrichment incidents.

This module is intentionally dependency-light: the backend image already has everything
needed to send a Telegram Bot API request through the standard library.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any

from core.config import settings

_MAX_DETAILS_CHARS = 1400


def send_admin_alert(
    *,
    title: str,
    message: str,
    level: str = "error",
    city_slug: str | None = None,
    job_id: int | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, object]:
    """Send a best-effort Telegram alert to the operations chat.

    Missing Telegram settings or Telegram API failures must never break the import
    worker. The return payload is primarily useful for tests and ad-hoc debugging.
    """
    token = settings.telegram_bot_token or settings.bot_token
    chat_id = settings.telegram_chat_id
    if not token or not chat_id:
        return {"sent": False, "reason": "not_configured"}

    text = _format_alert_text(
        title=title,
        message=message,
        level=level,
        city_slug=city_slug,
        job_id=job_id,
        details=details,
    )
    data = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": text,
            "disable_web_page_preview": "true",
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=data,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:  # noqa: S310 - configured bot API endpoint
            response.read()
        return {"sent": True}
    except Exception as exc:  # noqa: BLE001
        print(f"admin_alert_send_failed: {exc}")
        return {"sent": False, "reason": str(exc)[:300]}


def _format_alert_text(
    *,
    title: str,
    message: str,
    level: str,
    city_slug: str | None,
    job_id: int | None,
    details: dict[str, Any] | None,
) -> str:
    prefix = {
        "error": "❌",
        "warning": "⚠️",
        "info": "ℹ️",
    }.get(level, "⚠️")
    lines = [f"{prefix} City GO: {title}", message]
    if city_slug:
        lines.append(f"city: {city_slug}")
    if job_id is not None:
        lines.append(f"job: {job_id}")
    lines.append(f"time: {datetime.utcnow().isoformat(timespec='seconds')}Z")
    if details:
        compact = json.dumps(details, ensure_ascii=False, default=str)
        if len(compact) > _MAX_DETAILS_CHARS:
            compact = compact[:_MAX_DETAILS_CHARS] + "…"
        lines.append(f"details: {compact}")
    return "\n".join(lines)
