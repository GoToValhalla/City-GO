"""Обзор админки: actionable cards «что требует внимания»."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from models.admin_audit_log import AdminAuditLog
from models.city import City
from models.city_import_job import CityImportJob
from models.place import Place
from models.place_image import PLACE_IMAGE_STATUS_NEEDS_REVIEW, PlaceImage
from schemas.admin_ops import AdminActionCard


LOW_CONFIDENCE_LEVELS = ("low", "unknown")
VERIFICATION_QUEUE_STATUSES = ("needs_recheck", "unverified")
MANUAL_REVIEW_STATUSES = ("needs_review", "needs_manual_review", "deferred")
AUTO_BACKLOG_STATUSES = ("draft", "auto_backlog", "low_confidence")
ACTIVE_IMPORT_STATUSES = ("pending", "running")


def _card(code: str, title: str, count: int, severity: str, link_path: str, hint: str | None = None) -> AdminActionCard:
    return AdminActionCard(code=code, title=title, count=count, severity=severity, link_path=link_path, hint=hint)


def build_admin_overview(db: Session) -> dict[str, object]:
    place_counts = _place_overview_counts(db)
    pending_photos = _count_pending_photos(db)
    stuck_imports = _count_active_imports(db)
    cities_weak = _count_active_cities(db)
    audit_recent = _count_audit_rows(db)

    critical = [
        card
        for card in [
            _card("pending_photos", "Фото на модерации", pending_photos, "red" if pending_photos else "green", "/admin/photos"),
            _card("stuck_imports", "Зависшие импорты", stuck_imports, "yellow" if stuck_imports else "green", "/admin/imports"),
        ]
        if card.count > 0 or card.code == "pending_photos"
    ]
    data_quality = [
        _card("manual_review", "Требуют проверки", place_counts["manual_review"], _sev(place_counts["manual_review"], 20, 100), "/admin/verification?queue=manual", "Только явная ручная очередь."),
        _card("auto_backlog", "Не проверено авто", place_counts["auto_backlog"], _sev(place_counts["auto_backlog"], 500, 5000), "/admin/places?preset=auto_backlog", "Авто backlog для policy/enrichment, не ручная очередь."),
        _card("needs_verification", "Нужна автоперепроверка", place_counts["needs_verification"], _sev(place_counts["needs_verification"], 20, 100), "/admin/verification?queue=verification", "Verification backlog, не ручная очередь."),
        _card("no_photo", "Опубликовано без фото", place_counts["no_photo"], _sev(place_counts["no_photo"], 20, 100), "/admin/places?preset=no_photo"),
        _card("no_address", "Без адреса", place_counts["no_address"], _sev(place_counts["no_address"], 30, 150), "/admin/places?preset=no_address"),
        _card("no_description", "Без описания", place_counts["no_description"], _sev(place_counts["no_description"], 40, 200), "/admin/places?preset=no_description"),
        _card("low_confidence", "Низкая уверенность", place_counts["low_confidence"], _sev(place_counts["low_confidence"], 15, 80), "/admin/places?preset=low_confidence", "Quality bucket, не задача ручной модерации."),
        _card("not_route_eligible", "Исключены из маршрутов", place_counts["not_route_eligible"], "yellow" if place_counts["not_route_eligible"] else "green", "/admin/places?preset=not_in_routes"),
        _card("route_unknown", "Маршруты: нужно пересчитать", place_counts["route_unknown"], _sev(place_counts["route_unknown"], 10, 100), "/admin/places?preset=route_unknown"),
    ]
    operations = [_card("cities_total", "Активных городов", cities_weak, "green", "/admin/cities")]
    return {"critical": critical, "data_quality": data_quality, "operations": operations, "recent_audit_count": audit_recent, "generated_at": datetime.utcnow()}


def _place_overview_counts(db: Session) -> dict[str, int]:
    """Collect all place counters in one scan instead of N separate count() queries."""
    published = Place.is_published.is_(True)
    row = db.query(
        func.sum(case((published & Place.image_url.is_(None), 1), else_=0)).label("no_photo"),
        func.sum(case((published & Place.address.is_(None), 1), else_=0)).label("no_address"),
        func.sum(case((published & Place.short_description.is_(None), 1), else_=0)).label("no_description"),
        func.sum(case((published & Place.existence_confidence_level.in_(LOW_CONFIDENCE_LEVELS), 1), else_=0)).label("low_confidence"),
        func.sum(case((Place.publication_status.in_(MANUAL_REVIEW_STATUSES), 1), else_=0)).label("manual_review"),
        func.sum(case((Place.publication_status.in_(AUTO_BACKLOG_STATUSES), 1), else_=0)).label("auto_backlog"),
        func.sum(case((Place.verification_status.in_(VERIFICATION_QUEUE_STATUSES), 1), else_=0)).label("needs_verification"),
        func.sum(case((published & Place.is_route_eligible.is_not(True), 1), else_=0)).label("not_route_eligible"),
        func.sum(case((published & Place.is_route_eligible.is_(None), 1), else_=0)).label("route_unknown"),
    ).one()
    return {
        "no_photo": int(row.no_photo or 0),
        "no_address": int(row.no_address or 0),
        "no_description": int(row.no_description or 0),
        "low_confidence": int(row.low_confidence or 0),
        "manual_review": int(row.manual_review or 0),
        "auto_backlog": int(row.auto_backlog or 0),
        "needs_verification": int(row.needs_verification or 0),
        "not_route_eligible": int(row.not_route_eligible or 0),
        "route_unknown": int(row.route_unknown or 0),
    }


def _count_pending_photos(db: Session) -> int:
    return int(db.query(func.count(PlaceImage.id)).filter(PlaceImage.status == PLACE_IMAGE_STATUS_NEEDS_REVIEW).scalar() or 0)


def _count_active_imports(db: Session) -> int:
    return int(db.query(func.count(CityImportJob.id)).filter(CityImportJob.status.in_(ACTIVE_IMPORT_STATUSES)).scalar() or 0)


def _count_active_cities(db: Session) -> int:
    return int(db.query(func.count(City.id)).filter(City.is_active.is_(True), City.launch_status == "published").scalar() or 0)


def _count_audit_rows(db: Session) -> int:
    return int(db.query(func.count(AdminAuditLog.id)).scalar() or 0)


def _sev(count: int, yellow: int, red: int) -> str:
    if count >= red:
        return "red"
    if count >= yellow:
        return "yellow"
    return "green"
