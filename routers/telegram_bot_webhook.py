from fastapi import APIRouter, Header, HTTPException, Request

from core.config import settings
from telegram_bot.main import create_bot, feed_webhook_update

router = APIRouter(prefix="/telegram-bot", tags=["telegram-bot"])


@router.post("/webhook")
async def telegram_bot_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, bool]:
    if settings.bot_webhook_secret and x_telegram_bot_api_secret_token != settings.bot_webhook_secret:
        raise HTTPException(status_code=403, detail="Invalid Telegram webhook secret")
    if not settings.bot_token:
        raise HTTPException(status_code=503, detail="BOT_TOKEN is not configured")
    payload = await request.json()
    bot = create_bot()
    try:
        await feed_webhook_update(bot, payload)
    finally:
        await bot.session.close()
    return {"ok": True}
