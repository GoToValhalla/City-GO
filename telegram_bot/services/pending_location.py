from datetime import datetime, timedelta, timezone
from typing import Literal, TypedDict

from models.bot_session import BotSession

LocationIntent = Literal["nearby", "build_route", "continue_route"]
INTENT_TTL_SECONDS = 600
LOCATION_TTL_SECONDS = 900


class TemporaryLocation(TypedDict):
    lat: float
    lng: float
    expires_at: str


def set_pending_intent(session: BotSession, intent: LocationIntent) -> None:
    expires = _now() + timedelta(seconds=INTENT_TTL_SECONDS)
    session.current_flow = f"await_location:{intent}:{int(expires.timestamp())}"


def consume_pending_intent(session: BotSession) -> LocationIntent | None:
    flow = session.current_flow or ""
    parts = flow.split(":")
    if len(parts) != 3 or parts[0] != "await_location":
        return None
    session.current_flow = None
    if not parts[2].isdigit() or int(parts[2]) < int(_now().timestamp()):
        return None
    return parts[1] if parts[1] in {"nearby", "build_route", "continue_route"} else None


def save_temporary_location(session: BotSession, lat: float, lng: float) -> None:
    expires = _now() + timedelta(seconds=LOCATION_TTL_SECONDS)
    session.last_location = {"lat": lat, "lng": lng, "expires_at": expires.isoformat()}


def get_temporary_location(session: BotSession) -> TemporaryLocation | None:
    value = session.last_location
    if not isinstance(value, dict):
        return None
    try:
        expires = datetime.fromisoformat(str(value["expires_at"]))
        lat, lng = float(value["lat"]), float(value["lng"])
    except (KeyError, TypeError, ValueError):
        session.last_location = None
        return None
    if expires <= _now():
        session.last_location = None
        return None
    return {"lat": lat, "lng": lng, "expires_at": expires.isoformat()}


def clear_temporary_location(session: BotSession) -> None:
    session.last_location = None


def _now() -> datetime:
    return datetime.now(timezone.utc)
