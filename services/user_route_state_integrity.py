from __future__ import annotations

import hashlib
import hmac
import json
import os

from core.config import settings
from schemas.user_route import UserRouteState

_TEST_SECRET = "city-go-test-route-state-integrity"
_MIN_SECRET_BYTES = 32
_FORBIDDEN_RUNTIME_SECRETS = frozenset(
    {
        _TEST_SECRET,
        "dev_fallback_secret_key_12345",
        "change-me",
        "changeme",
        "secret",
    }
)
_FORBIDDEN_RUNTIME_SECRETS_CASEFOLD = frozenset(
    item.casefold() for item in _FORBIDDEN_RUNTIME_SECRETS
)


class UserRouteStateIntegrityError(ValueError):
    pass


def sign_user_route_state(state: UserRouteState) -> UserRouteState:
    token = hmac.new(_secret(), _canonical_payload(state), hashlib.sha256).hexdigest()
    return state.model_copy(update={"state_token": token})


def verify_user_route_state(state: UserRouteState) -> None:
    supplied = str(state.state_token or "")
    if not supplied and _allow_unsigned_test_state():
        return
    expected = hmac.new(_secret(), _canonical_payload(state), hashlib.sha256).hexdigest()
    if not supplied or not hmac.compare_digest(supplied, expected):
        raise UserRouteStateIntegrityError("Route state signature is missing or invalid.")


def validate_route_state_runtime_config() -> None:
    """Fail application startup when signing configuration is unsafe."""
    if _is_test():
        return
    try:
        _validated_runtime_secret()
    except UserRouteStateIntegrityError as exc:
        # Preserve the established startup contract while runtime sign/verify
        # continues to expose an integrity-domain error.
        raise RuntimeError(str(exc)) from exc


def _canonical_payload(state: UserRouteState) -> bytes:
    payload = state.model_dump(mode="json", exclude={"state_token"})
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _secret() -> bytes:
    configured = str(settings.user_route_state_secret or "").strip()
    if _is_test():
        return (configured or _TEST_SECRET).encode("utf-8")
    return _validated_runtime_secret()


def _validated_runtime_secret() -> bytes:
    configured = str(settings.user_route_state_secret or "").strip()
    if not configured:
        raise UserRouteStateIntegrityError(
            "USER_ROUTE_STATE_SECRET is required outside the test runtime."
        )
    encoded = configured.encode("utf-8")
    if len(encoded) < _MIN_SECRET_BYTES:
        raise UserRouteStateIntegrityError(
            f"USER_ROUTE_STATE_SECRET must contain at least {_MIN_SECRET_BYTES} bytes."
        )
    if configured.casefold() in _FORBIDDEN_RUNTIME_SECRETS_CASEFOLD:
        raise UserRouteStateIntegrityError(
            "USER_ROUTE_STATE_SECRET uses a forbidden default or test value."
        )
    return encoded


def _allow_unsigned_test_state() -> bool:
    environment = str(settings.app_env or "").strip().lower()
    return _is_test() and environment not in {"prod", "production"}


def _is_test() -> bool:
    return bool(os.environ.get("PYTEST_CURRENT_TEST"))
