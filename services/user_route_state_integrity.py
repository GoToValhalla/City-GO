from __future__ import annotations

import hashlib
import hmac
import json
import os

from core.config import settings
from schemas.user_route import UserRouteState

_TEST_SECRET = "city-go-test-route-state-integrity"


class UserRouteStateIntegrityError(ValueError):
    pass


def sign_user_route_state(state: UserRouteState) -> UserRouteState:
    token = hmac.new(_secret(), _canonical_payload(state), hashlib.sha256).hexdigest()
    return state.model_copy(update={"state_token": token})


def verify_user_route_state(state: UserRouteState) -> None:
    supplied = str(state.state_token or "")
    if not supplied and _is_test():
        return
    expected = hmac.new(_secret(), _canonical_payload(state), hashlib.sha256).hexdigest()
    if not supplied or not hmac.compare_digest(supplied, expected):
        raise UserRouteStateIntegrityError("Route state signature is missing or invalid.")


def validate_route_state_runtime_config() -> None:
    """Fail before serving traffic; APP_ENV is not trusted as a security boundary."""
    if _is_test():
        return
    if not str(settings.user_route_state_secret or "").strip():
        raise RuntimeError("USER_ROUTE_STATE_SECRET is required outside the test runtime.")


def _canonical_payload(state: UserRouteState) -> bytes:
    payload = state.model_dump(mode="json", exclude={"state_token"})
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _secret() -> bytes:
    configured = str(settings.user_route_state_secret or "").strip()
    if configured:
        return configured.encode("utf-8")
    if _is_test():
        return _TEST_SECRET.encode("utf-8")
    raise UserRouteStateIntegrityError("USER_ROUTE_STATE_SECRET is required outside the test runtime.")


def _is_test() -> bool:
    return bool(os.environ.get("PYTEST_CURRENT_TEST"))
