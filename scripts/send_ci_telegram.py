#!/usr/bin/env python3
"""Send CI notification message to Telegram."""

from __future__ import annotations

import argparse
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path


def main() -> int:
    """Read a message file and send it to Telegram when secrets are configured."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--message-file", required=True, type=Path)
    parser.add_argument("--fallback", required=True)
    args = parser.parse_args()

    token = os.getenv("TG_TOKEN", "").strip()
    chat_id = os.getenv("TG_CHAT", "").strip()
    if not token or not chat_id:
        print("Telegram notification skipped: missing Telegram secrets")
        return 0

    text = args.message_file.read_text(encoding="utf-8") if args.message_file.exists() else args.fallback
    payload = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": "true",
    }).encode("utf-8")
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        print(response.read().decode("utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
