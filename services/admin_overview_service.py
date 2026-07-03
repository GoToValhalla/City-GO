"""Admin overview actionable cards."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from models.admin_audit_log import AdminAuditLog
from models.city import City
from models.city_import_job import CityImportJob
from models.place import Place
from models.place_image import PLACE_IMAGE_STATUS_NEEDS_REVIEW, PlaceImage
from schemas.admin_ops import AdminActionCard
from services.route_eligibility_policy import HARD_EXCLUDED_CATEGORIES

LOW_CONFIDENCE_LEVELS = ("low", "unknown")
VERIFICATION_QUEUE_STATUSES = ("needs_recheck", "unverified")
MANUAL_REVIEW_STATUSES = ("needs_review", "needs_manual_review", "deferred")
AUTO_BACKLOG_STATUSES = ("draft", "auto_backlog", "low_confidence")
ACTIVE_IMPORT_STATUSES = ("pending", "running")
MIN_DESCRIPTION_LENGTH = 40
GENERIC_DESCRIPTION_MARKERS = ("описание будет добавлено", "нет описания", "description pending", "todo")
EXCLUDED_CATEGORIES = tuple(sorted(HARD_EXCLUDED_CATEGORIES))


def _card(code: str, title: str, count: int, severity: str, link_path: str, hint: str | None = None, action_label: str | None = None) -> AdminActionCard:
    return AdminActionCard(code=code, title=title, count=count, severity=severity, link_path=link_path, hint=hint, action_label=action_label)


def build_admin_overview(db: Session) -> dict[str, object]:
    place_counts = _place_overview_counts(db)
    policy_counts = _policy_counts(db)
    ops = _operational_counts(db)

    critical = [
        card
        for card in [
            _card("pending_photos", "Фото на модерации", ops["pending_photos"], "red" if ops["pending_photos"] else "green", "/admin/photos", action_label="Открыть фото"),
            _card("stuck_imports", "Зависшие импорты", ops["stuck_imports"], "yellow" if ops["stuck_imports"] else "green", "/admin/imports", action_label="Открыть импорты"),
        ]
        if card.count > 0 or card.code == "pending_photos"
    ]
    data_quality = [
        _card("route_blockers", "Не попадут в маршруты", policy_counts["blocked"], _sev(policy_counts["blocked"], 10, 100), "/admin/places?preset=not_in_routes", "Published/catalog places, которые не проходят route policy.", "Открыть блокеры"),
        _card("not_route_eligible", "Исключены из маршрутов", policy_counts["not_route_eligible"], _sev(policy_counts["not_route_eligible"], 10, 100), "/admin/places?preset=not_in_routes", "Опубликованные места с is_route_eligible=false.", "Открыть исключённые"),
        _card("route_unknown", "Маршруты: неизвестная категория", policy_counts["unknown"], _sev(policy_counts["unknown"], 10, 100), "/admin/places?preset=route_unknown", "Нужно исправить canonical category или пересчитать taxonomy.", "Открыть unknown"),
        _card("route_excluded", "Сервисные точки опубликованы", policy_counts["excluded"], _sev(policy_counts["excluded"], 1, 20), "/admin/places?preset=service_places", "Сервисные точки в published/catalog слое.", "Открыть сервисные"),
        _card("auto_backlog", "Автоочередь enrichment/policy", place_counts["auto_backlog"], _sev(place_counts["auto_backlog"], 500, 5000), "/admin/places?publication=auto_backlog", "Не ручная модерация: запускать автообогащение и пересчёт policy.", "Открыть авто"),
        _card("manual_review", "Ручная проверка", place_counts["manual_review"], _sev(place_counts["manual_review"], 20, 100), "/admin/places?publication=needs_review", "Только то, что автоматом нельзя решить.", "Открыть ручную очередь"),
        _card("needs_verification", "Автоперепроверка", place_counts["needs_verification"], _sev(place_counts["needs_verification"], 100, 1000), "/admin/places?verification=needs_recheck", "Verification backlog, не ручная очередь.", "Открыть verification"),
        _card("no_photo", "Опубликовано без фото", place_counts["no_photo"], _sev(place_counts["no_photo"], 20, 100), "/admin/places?preset=no_photo", action_label="Открыть фото debt"),
        _card("no_address", "Без адреса", place_counts["no_address"], _sev(place_counts["no_address"], 30, 150), "/admin/places?preset=no_address", action_label="Открыть адреса"),
        _card("no_description", "Без описания", place_counts["no_description"], _sev(place_counts["no_description"], 40, 200), "/admin/places?preset=no_description", "Пустое или слишком короткое описание.", "Открыть описания"),
        _card("low_confidence", "Низкая уверенность", place_counts["low_confidence"], _sev(place_counts["low_confidence"], 15, 80), "/admin/places?confidence=true", "Critical confidence bucket, не общая ручная очередь.", "Открыть confidence"),
    ]
    operations = [_card("cities_total", "Активных городов", ops["active_cities"], "green", "/admin/cities", action_label="Открыть города")]
    return {"critical": critical, "data_quality": data_quality, "operations": operations, "recent_audit_count": ops["audit_recent"], "generated_at": datetime.utcnow()}


def _place_overview_counts(db: Session) -> dict[str, int]:
    published = _published_catalog_condition()
    row = db.query(
        func.sum(case((published & _missing_text(Place.image_url), 1), else_=0)).label("no_photo"),
        func.sum(case((published & _missing_text(Place.address), 1), else_=0)).label("no_address"),
        func.sum(case((published & _missing_description_condition(), 1), else_=0)).label("no_description"),
        func.sum(case((published & Place.existence_confidence_level.in_(LOW_CONFIDENCE_LEVELS), 1), else_=0)).label("low_confidence"),
        func.sum(case((Place.publication_status.in_(MANUAL_REVIEW_STATUSES), 1), else_=0)).label("manual_review"),
        func.sum(case((Place.publication_status.in_(AUTO_BACKLOG_STATUSES), 1), else_=0)).label("auto_backlog"),
        func.sum(case((Place.verification_status.in_(VERIFICATION_QUEUE_STATUSES), 1), else_=0)).label("needs_verification"),
    ).one()
    return {key: int(getattr(row, key) or 0) for key in ("no_photo", "no_address", "no_description", "low_confidence", "manual_review", "auto_backlog", "needs_verification")}


def _policy_counts(db: Session) -> dict[str, int]:
    published = _published_catalog_condition()
    excluded = _excluded_category_condition()
    unknown = _unknown_category_condition()
    blocked = published & or_(Place.is_route_eligible.is_not(True), Place.lat.is_(None), Place.lng.is_(None), excluded, unknown)
    row = db.query(
        func.sum(case((blocked, 1), else_=0)).label("blocked"),
        func.sum(case((published & Place.is_route_eligible.is_not(True), 1), else_=0)).label("not_route_eligible"),
        func.sum(case((published & unknown, 1), else_=0)).label("unknown"),
        func.sum(case((published & excluded, 1), else_=0)).label("excluded"),
    ).one()
    return {key: int(getattr(row, key) or 0) for key in ("blocked", "not_route_eligible", "unknown", "excluded")}


def _operational_counts(db: Session) -> dict[str, int]:
    row = db.query(
        db.query(func.count(PlaceImage.id)).filter(PlaceImage.status == PLACE_IMAGE_STATUS_NEEDS_REVIEW).scalar_subquery().label("pending_photos"),
        db.query(func.count(CityImportJob.id)).filter(CityImportJob.status.in_(ACTIVE_IMPORT_STATUSES)).scalar_subquery().label("stuck_imports"),
        db.query(func.count(City.id)).filter(City.is_active.is_(True), City.launch_status == "published").scalar_subquery().label("active_cities"),
        db.query(func.count(AdminAuditLog.id)).scalar_subquery().label("audit_recent"),
    ).one()
    return {key: int(getattr(row, key) or 0) for key in ("pending_photos", "stuck_imports", "active_cities", "audit_recent")}


def _published_catalog_condition():
    return Place.is_active.is_(True) & Place.is_published.is_(True) & Place.is_visible_in_catalog.is_(True) & or_(Place.status.is_(None), Place.status == "active")


def _excluded_category_condition():
    return or_(Place.canonical_category.in_(EXCLUDED_CATEGORIES), Place.category.in_(EXCLUDED_CATEGORIES))


def _unknown_category_condition():
    return or_(Place.canonical_category.is_(None), Place.canonical_category == "unknown", Place.category == "unknown")


def _missing_text(column):
    return or_(column.is_(None), func.length(func.trim(column)) == 0)


def _missing_description_condition():
    text = func.lower(func.trim(Place.short_description))
    return or_(Place.short_description.is_(None), func.length(func.trim(Place.short_description)) < MIN_DESCRIPTION_LENGTH, text == func.lower(func.trim(Place.title)), *[text.contains(marker) for marker in GENERIC_DESCRIPTION_MARKERS])


def _sev(count: int, yellow: int, red: int) -> str:
    if count >= red:
        return "red"
    if count >= yellow:
        return "yellow"
    return "green"
