import hmac

from fastapi import APIRouter, Header, HTTPException, Request

from core.config import settings
from telegram_bot.main import create_bot, feed_webhook_update

router = APIRouter(prefix="/telegram-bot", tags=["telegram-bot"])


def _is_production() -> bool:
    return str(settings.app_env or "").strip().lower() in {"prod", "production"}


@router.post("/webhook")
async def telegram_bot_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, bool]:
    expected = str(settings.bot_webhook_secret or "").strip()
    if not expected:
        if _is_production():
            raise HTTPException(status_code=503, detail="Telegram webhook secret is not configured")
        raise HTTPException(status_code=503, detail="Telegram webhook secret is not configured")
    provided = str(x_telegram_bot_api_secret_token or "")
    if not hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8")):
        raise HTTPException(status_code=403, detail="Invalid Telegram webhook secret")
    if not (settings.bot_token or settings.telegram_bot_token):
        raise HTTPException(status_code=503, detail="BOT_TOKEN/TELEGRAM_BOT_TOKEN is not configured")
    payload = await request.json()
    bot = create_bot()
    try:
        await feed_webhook_update(bot, payload)
    finally:
        await bot.session.close()
    return {"ok": True}
