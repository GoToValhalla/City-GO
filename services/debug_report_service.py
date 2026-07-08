from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy.orm import Query, Session

from core.config import settings
from core.version import get_backend_version
from models.debug_report import DebugReport
from schemas.debug_report import DebugReportCreate
from services.admin_alert_service import send_admin_alert
from services.system_log_service import write_system_log

SECRET_KEYS = {"authorization", "cookie", "set-cookie", "token", "access_token", "refresh_token", "password", "secret", "api_key", "apikey"}


def create_debug_report(db: Session, payload: DebugReportCreate) -> DebugReport:
    sanitized = sanitize_report(payload)
    row = DebugReport(
        public_id=_public_id(),
        environment=settings.app_env,
        app_version=get_backend_version().get("commit") or get_backend_version().get("version"),
        **{key: sanitized.get(key) for key in _MODEL_KEYS if key in sanitized},
        sanitized_payload=sanitized,
    )
    db.add(row)
    db.flush()
    _send_telegram_if_enabled(db, row)
    return row


def sanitize_report(payload: DebugReportCreate) -> dict[str, Any]:
    raw = payload.model_dump(exclude={"allow_precise_coordinates"})
    cleaned = _sanitize(raw)
    if not payload.allow_precise_coordinates:
        cleaned["location_context"] = _coarse_location(cleaned.get("location_context"))
    cleaned["title"] = str(cleaned.get("title") or "Debug report")[:255]
    cleaned["summary"] = str(cleaned.get("summary") or "No summary")[:4000]
    return cleaned


def list_debug_reports(
    db: Session,
    *,
    city_slug: str | None = None,
    screen: str | None = None,
    category: str | None = None,
    severity: str | None = None,
    request_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[DebugReport], int]:
    query = _filtered(db.query(DebugReport), city_slug=city_slug, screen=screen, category=category, severity=severity, request_id=request_id)
    return query.order_by(DebugReport.created_at.desc(), DebugReport.id.desc()).offset(offset).limit(limit).all(), query.count()


def get_debug_report(db: Session, id_or_public_id: str) -> DebugReport | None:
    if id_or_public_id.isdigit():
        found = db.get(DebugReport, int(id_or_public_id))
        if found is not None:
            return found
    return db.query(DebugReport).filter(DebugReport.public_id == id_or_public_id).first()


def admin_url(row: DebugReport) -> str:
    base = (settings.citygo_debug_reports_admin_base_url or "").rstrip("/")
    path = f"/admin/debug-reports/{row.public_id}"
    return f"{base}{path}" if base else path


def copied_summary(row: DebugReport) -> str:
    lines = [
        f"Debug report: {row.public_id}",
        f"Screen: {row.screen}",
        f"Severity: {row.severity}",
        f"City: {row.city_slug or '-'}",
        f"Request ID: {row.request_id or '-'}",
        f"URL: {row.url or '-'}",
        f"Summary: {row.summary}",
        f"Report: {admin_url(row)}",
    ]
    return "\n".join(lines)


def _send_telegram_if_enabled(db: Session, row: DebugReport) -> None:
    if not settings.citygo_debug_reports_telegram_enabled:
        row.telegram_sent = False
        row.telegram_error = "telegram_disabled"
        return
    result = send_admin_alert(
        title="Import pipeline failed" if row.category == "import" else "Debug Report",
        message=_telegram_message(row),
        level="error" if row.severity in {"error", "critical"} else "warning",
        city_slug=row.city_slug,
        job_id=_import_job_id(row),
        details={"report": admin_url(row), "screen": row.screen, "request_id": row.request_id},
        chat_id_override=settings.citygo_debug_reports_telegram_chat_id or None,
    )
    row.telegram_sent = bool(result.get("sent"))
    row.telegram_error = None if row.telegram_sent else str(result.get("reason") or "not_sent")[:500]
    if not row.telegram_sent:
        write_system_log(
            db, level="warning", module="debug_report",
            message=f"Telegram send failed for debug report {row.public_id}: {row.telegram_error}",
            details={"public_id": row.public_id, "reason": row.telegram_error, "screen": row.screen, "request_id": row.request_id},
            city_slug=row.city_slug, request_id=row.request_id, commit=False,
        )


def _telegram_message(row: DebugReport) -> str:
    label = "Import Issue" if row.category == "import" else "Debug Report"
    return f"CITY GO · {label}\nScreen: {row.screen}\nIssue: {row.summary[:180]}\nRequest ID: {row.request_id or '-'}\nReport: {admin_url(row)}"


def _import_job_id(row: DebugReport) -> int | None:
    context = row.backend_context or {}
    value = context.get("city_admin_import_job_id") or context.get("import_job_id")
    return int(value) if isinstance(value, int) or (isinstance(value, str) and value.isdigit()) else None


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _redacted(key, item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value[:500]]
    if isinstance(value, str):
        return _strip_secret_patterns(value)[:8000]
    return value


def _redacted(key: str, value: Any) -> Any:
    lowered = key.strip().lower().replace("-", "_")
    if lowered in SECRET_KEYS or any(part in lowered for part in ("token", "secret", "password", "authorization", "cookie")):
        return "[REDACTED]"
    return _sanitize(value)


def _strip_secret_patterns(value: str) -> str:
    value = re.sub(r"Bearer\s+[A-Za-z0-9._~+/=-]+", "Bearer [REDACTED]", value)
    return re.sub(r"(password|token|secret|api_key)=([^&\s]+)", r"\1=[REDACTED]", value, flags=re.IGNORECASE)


def _coarse_location(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return value
    result = dict(value)
    for key in ("lat", "lng", "latitude", "longitude"):
        if isinstance(result.get(key), (int, float)):
            result[key] = round(float(result[key]), 2)
    if isinstance(result.get("coordinates"), dict):
        result["coordinates"] = _coarse_location(result["coordinates"])
    return result


def _filtered(query: Query, **filters: str | None) -> Query:
    for key, value in filters.items():
        if value:
            query = query.filter(getattr(DebugReport, key) == value)
    return query


def _public_id() -> str:
    return f"DBG-{uuid.uuid4().hex[:10].upper()}"


_MODEL_KEYS = (
    "screen", "severity", "category", "city_slug", "destination_slug", "place_id", "route_id",
    "request_id", "url", "user_action", "title", "summary", "user_comment", "frontend_state",
    "request_payload", "response_summary", "response_payload", "debug_trace", "warnings",
    "reason_codes", "linked_entities", "browser", "location_context", "backend_context",
)
