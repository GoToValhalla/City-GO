"""Polling entrypoint for the City GO Telegram bot."""

import logging

from telegram_bot.main import main


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Telegram bot stopped manually.")
