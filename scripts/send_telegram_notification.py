#!/usr/bin/env python3
"""Send a plain-text Telegram operations notification with retries and validation."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def send_message(*, token: str, chat_id: str, text: str, attempts: int = 3) -> None:
    if not token or not chat_id:
        raise RuntimeError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are required")
    payload = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text[:4000],
        "disable_web_page_preview": "true",
    }).encode("utf-8")
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(request, timeout=15) as response:  # noqa: S310
                body = json.loads(response.read().decode("utf-8"))
            if body.get("ok") is not True:
                raise RuntimeError(f"Telegram API rejected message: {body}")
            return
        except (OSError, ValueError, urllib.error.URLError) as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(attempt * 2)
    raise RuntimeError(f"Telegram notification failed after {attempts} attempts: {last_error}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--text")
    parser.add_argument("--text-file", type=Path)
    parser.add_argument("--allow-missing", action="store_true")
    args = parser.parse_args()

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        if args.allow_missing:
            print("telegram_notification_skipped: credentials are missing")
            return 0
        print("telegram_notification_failed: credentials are missing", file=sys.stderr)
        return 2

    text = args.text_file.read_text(encoding="utf-8") if args.text_file else (args.text or "")
    if not text.strip():
        print("telegram_notification_failed: message is empty", file=sys.stderr)
        return 2
    try:
        send_message(token=token, chat_id=chat_id, text=text)
    except RuntimeError as exc:
        print(f"telegram_notification_failed: {exc}", file=sys.stderr)
        return 1
    print("telegram_notification_sent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
