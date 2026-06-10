#!/usr/bin/env bash

set -e

echo "Starting City GO Telegram bot..."

if [ -d ".venv" ]; then
  source .venv/bin/activate
fi

python3 telegram_bot_main.py
