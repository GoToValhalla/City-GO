from __future__ import annotations

import hashlib
import hmac
import json

from core.config import settings
from schemas.user_route import UserRouteState

_LOCAL_SECRET = "city-go-local-route-state-integrity"


class UserRouteStateIntegrityError(ValueError):
    pass


def sign_user_route_state(state: UserRouteState) -> UserRouteState:
    token = hmac.new(_secret(), _canonical_payload(state), hashlib.sha256).hexdigest()
    return state.model_copy(update={"state_token": token})


def verify_user_route_state(state: UserRouteState) -> None:
    supplied = str(state.state_token or "")
    if not supplied and not _is_production():
        # Legacy local/unit fixtures remain usable. Production never permits
        # unsigned route state and always requires a dedicated secret.
        return
    expected = hmac.new(_secret(), _canonical_payload(state), hashlib.sha256).hexdigest()
    if not supplied or not hmac.compare_digest(supplied, expected):
        raise UserRouteStateIntegrityError("Route state signature is missing or invalid.")


def _canonical_payload(state: UserRouteState) -> bytes:
    payload = {
        "route_id": str(state.route_id),
        "revision": int(state.revision),
        "city_slug": str(state.context.city_id or ""),
        "place_ids": [str(point.place_id) for point in state.points],
    }
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _secret() -> bytes:
    configured = str(settings.user_route_state_secret or "").strip()
    if configured:
        return configured.encode("utf-8")
    if _is_production():
        raise UserRouteStateIntegrityError("USER_ROUTE_STATE_SECRET is required in production.")
    return _LOCAL_SECRET.encode("utf-8")


def _is_production() -> bool:
    return str(settings.app_env or "").strip().lower() in {"prod", "production"}
