from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from schemas.user_route import RouteUserWarning, UserRouteState
from services.route_user_warnings import route_warning_message

RAW_TECHNICAL_CODE = re.compile(r"^[a-z0-9]+(?:_[a-z0-9]+){1,}$")
PUBLIC_WARNING_TYPES = {"route", "data", "budget", "walk", "interest"}
PUBLIC_SEVERITIES = {"info", "warning", "error"}
DEFAULT_ACTION_HINT = "Проверьте детали маршрута перед стартом."
# Keep aligned with scripts/route_public_contract_gate.py markers.
FORBIDDEN_DIAGNOSTIC_MARKERS = (
    "secret",
    "token",
    "password",
    "passwd",
    "bearer ",
    "authorization",
    "database_url",
    "postgres://",
    "sqlite:///",
    "traceback",
)
SUPPRESSED_DIAGNOSTIC = "Diagnostic detail suppressed."


def sanitize_user_route_state(state: UserRouteState) -> UserRouteState:
    """Final public API gate for user-facing route fields.

    Route assembly services may still operate with internal warning codes. Public
    endpoints must never expose those codes in fields rendered by the client.
    """
    warnings = [_public_text(item) for item in list(state.warnings or [])]
    user_warnings = [_public_warning_item(item) for item in list(state.user_warnings or [])]
    explanation = _sanitize_value(dict(state.explanation or {}))
    debug_trace = [_sanitize_debug_entry(item) for item in list(state.debug_trace or [])]
    return state.model_copy(
        update={
            "partial_reason": _public_text(state.partial_reason),
            "warnings": warnings,
            "user_warnings": user_warnings,
            "warning_count": len(warnings) if warnings else len(user_warnings),
            "has_warnings": bool(warnings or user_warnings),
            "explanation": explanation if isinstance(explanation, dict) else {},
            "debug_trace": debug_trace,
        }
    )


def _public_warning_item(value: Any) -> RouteUserWarning:
    data = _as_mapping(value)
    kind = str(data.get("type") or "route").strip()
    severity = str(data.get("severity") or "warning").strip()
    message = _public_text(data.get("user_message") or data.get("message") or "")
    hint = _public_text(data.get("action_hint") or DEFAULT_ACTION_HINT)
    place_ids = data.get("affected_place_ids") or []
    if _is_raw_code(kind) or kind not in PUBLIC_WARNING_TYPES:
        kind = "route"
    if severity not in PUBLIC_SEVERITIES:
        severity = "warning"
    return RouteUserWarning(
        type=kind,
        severity=severity,
        user_message=message or route_warning_message("unknown_internal_code"),
        affected_place_ids=[str(item) for item in place_ids] if isinstance(place_ids, Sequence) and not isinstance(place_ids, (str, bytes, bytearray)) else [],
        action_hint=hint or DEFAULT_ACTION_HINT,
    )


def _sanitize_value(value: Any) -> Any:
    if isinstance(value, str):
        return _public_text(value)
    if isinstance(value, Mapping):
        return {str(key): _sanitize_value(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_sanitize_value(item) for item in value]
    return value


def _public_text(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    return route_warning_message(text) if _is_raw_code(text) else text


def _sanitize_debug_entry(value: Any) -> dict[str, Any]:
    data = _as_mapping(value)
    return {str(key): _sanitize_debug_value(item) for key, item in data.items()}


def _sanitize_debug_value(value: Any) -> Any:
    if isinstance(value, str):
        return _sanitize_debug_text(value)
    if isinstance(value, Mapping):
        return {str(key): _sanitize_debug_value(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_sanitize_debug_value(item) for item in value]
    return value


def _sanitize_debug_text(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    lowered = text.casefold()
    if any(marker in lowered for marker in FORBIDDEN_DIAGNOSTIC_MARKERS):
        return SUPPRESSED_DIAGNOSTIC
    return text


def _is_raw_code(value: str) -> bool:
    return bool(RAW_TECHNICAL_CODE.fullmatch(str(value or "").strip()))


def _as_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    if hasattr(value, "model_dump"):
        dumped = value.model_dump()
        return dumped if isinstance(dumped, Mapping) else {}
    return {}
