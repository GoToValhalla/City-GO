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
from schemas.admin_ops import AdminActionCard, AdminOwner, AdminPrimaryAction, AdminQueueType
from services.route_eligibility_policy import HARD_EXCLUDED_CATEGORIES

LOW_CONFIDENCE_LEVELS = ("low", "unknown")
VERIFICATION_QUEUE_STATUSES = ("needs_recheck", "unverified")
MANUAL_REVIEW_STATUSES = ("needs_review", "needs_manual_review", "deferred")
AUTO_BACKLOG_STATUSES = ("draft", "auto_backlog", "low_confidence")
ACTIVE_IMPORT_STATUSES = ("pending", "running")
MIN_DESCRIPTION_LENGTH = 40
GENERIC_DESCRIPTION_MARKERS = ("описание будет добавлено", "нет описания", "description pending", "todo", "вставьте описание")
NON_SERVICE_ROUTE_CATEGORIES = {"unknown", "other", "useful"}
EXCLUDED_CATEGORIES = tuple(sorted(HARD_EXCLUDED_CATEGORIES - NON_SERVICE_ROUTE_CATEGORIES))


def _card(
    code: str,
    title: str,
    count: int,
    severity: str,
    link_path: str,
    short_hint: str,
    action_label: str,
    *,
    queue_type: AdminQueueType,
    primary_action: AdminPrimaryAction,
    sample_endpoint: str | None,
    owner: AdminOwner,
    is_human_actionable: bool,
    mobile_priority: str,
    hint: str | None = None,
) -> AdminActionCard:
    return AdminActionCard(
        code=code,
        title=title,
        count=count,
        severity=severity,
        link_path=link_path,
        hint=hint or short_hint,
        action_label=action_label,
        queue_type=queue_type,
        primary_action=primary_action,
        short_hint=short_hint,
        sample_endpoint=sample_endpoint,
        owner=owner,
        is_human_actionable=is_human_actionable,
        mobile_priority=mobile_priority,
    )


def build_admin_overview(db: Session) -> dict[str, object]:
    place_counts = _place_overview_counts(db)
    policy_counts = _policy_counts(db)
    ops = _operational_counts(db)

    critical = [
        card
        for card in [
            _card("pending_photos", "Фото на проверке", ops["pending_photos"], "red" if ops["pending_photos"] else "green", "/admin/photos", "Нужно принять или отклонить фото.", "Открыть фото", queue_type="manual_review", primary_action="review_items", sample_endpoint=None, owner="content", is_human_actionable=True, mobile_priority="high"),
            _card("stuck_imports", "Зависшие импорты", ops["stuck_imports"], "yellow" if ops["stuck_imports"] else "green", "/admin/imports", "Проверьте задачи загрузки городов.", "Открыть импорты", queue_type="operation", primary_action="open_report", sample_endpoint=None, owner="platform", is_human_actionable=True, mobile_priority="medium"),
        ]
        if card.count > 0 or card.code == "pending_photos"
    ]
    data_quality = [
        _card("route_blockers", "Проблемы маршрутов", policy_counts["blocked"], _sev(policy_counts["blocked"], 10, 100), "/admin/places?preset=route_blockers", "Эти места сейчас не попадут в маршруты.", "Открыть проблемы", queue_type="route_blocker", primary_action="open_queue", sample_endpoint="/admin/places/search?preset=route_blockers", owner="data", is_human_actionable=True, mobile_priority="high"),
        _card("not_route_eligible", "Отключены вручную", policy_counts["not_route_eligible"], _sev(policy_counts["not_route_eligible"], 10, 100), "/admin/places?preset=published_not_route_eligible", "Места, явно отключённые от маршрутов.", "Открыть отключённые", queue_type="route_blocker", primary_action="open_queue", sample_endpoint="/admin/places/search?preset=published_not_route_eligible", owner="data", is_human_actionable=True, mobile_priority="medium"),
        _card("route_unknown", "Неизвестные категории", policy_counts["unknown"], _sev(policy_counts["unknown"], 10, 100), "/admin/places?preset=route_unknown", "Нужно назначить понятную категорию.", "Разобрать категории", queue_type="taxonomy_gap", primary_action="fix_taxonomy", sample_endpoint="/admin/places/search?preset=route_unknown", owner="taxonomy", is_human_actionable=True, mobile_priority="high"),
        _card("route_excluded", "Сервисные точки", policy_counts["excluded"], _sev(policy_counts["excluded"], 1, 20), "/admin/places?preset=service_places", "Скрыть из маршрутов аптеки, банки, остановки и сервисные POI.", "Открыть сервисные", queue_type="route_blocker", primary_action="open_queue", sample_endpoint="/admin/places/search?preset=service_places", owner="data", is_human_actionable=True, mobile_priority="medium"),
        _card("auto_backlog", "Автоисправление", place_counts["auto_backlog"], _sev(place_counts["auto_backlog"], 500, 5000), "/admin/places?preset=auto_backlog", "Очередь для автоматического обогащения и пересчёта.", "Открыть автоочередь", queue_type="auto_fix", primary_action="run_auto_fix", sample_endpoint="/admin/places/search?preset=auto_backlog", owner="automation", is_human_actionable=False, mobile_priority="medium"),
        _card("manual_review", "Ручная проверка", place_counts["manual_review"], _sev(place_counts["manual_review"], 20, 100), "/admin/places?preset=manual_review", "Здесь нужны решения оператора.", "Проверить вручную", queue_type="manual_review", primary_action="review_items", sample_endpoint="/admin/places/search?preset=manual_review", owner="content", is_human_actionable=True, mobile_priority="high"),
        _card("needs_verification", "Автоперепроверка", place_counts["needs_verification"], _sev(place_counts["needs_verification"], 100, 1000), "/admin/places?preset=needs_verification", "Очередь автоматической проверки данных.", "Открыть очередь", queue_type="verification_backlog", primary_action="run_auto_fix", sample_endpoint="/admin/places/search?preset=needs_verification", owner="automation", is_human_actionable=False, mobile_priority="low"),
        _card("no_photo", "Без фото", place_counts["no_photo"], _sev(place_counts["no_photo"], 20, 100), "/admin/places?preset=published_no_photo", "Добавьте фото к опубликованным местам.", "Добавить фото", queue_type="content_gap", primary_action="enrich_content", sample_endpoint="/admin/places/search?preset=published_no_photo", owner="content", is_human_actionable=True, mobile_priority="medium"),
        _card("no_address", "Без адреса", place_counts["no_address"], _sev(place_counts["no_address"], 30, 150), "/admin/places?preset=published_no_address", "Уточните адрес для карточек мест.", "Исправить адреса", queue_type="content_gap", primary_action="enrich_content", sample_endpoint="/admin/places/search?preset=published_no_address", owner="content", is_human_actionable=True, mobile_priority="medium"),
        _card("no_description", "Без описания", place_counts["no_description"], _sev(place_counts["no_description"], 40, 200), "/admin/places?preset=published_no_description", "Нужно добавить нормальное описание.", "Добавить описания", queue_type="content_gap", primary_action="enrich_content", sample_endpoint="/admin/places/search?preset=published_no_description", owner="content", is_human_actionable=True, mobile_priority="medium"),
        _card("low_confidence", "Низкая уверенность", place_counts["low_confidence"], _sev(place_counts["low_confidence"], 15, 80), "/admin/places?preset=published_low_confidence", "Данные места нужно перепроверить.", "Открыть проверку", queue_type="verification_backlog", primary_action="run_auto_fix", sample_endpoint="/admin/places/search?preset=published_low_confidence", owner="automation", is_human_actionable=False, mobile_priority="low"),
    ]
    operations = [_card("cities_total", "Активные города", ops["active_cities"], "green", "/admin/cities", "Города, доступные операторам.", "Открыть города", queue_type="operation", primary_action="open_report", sample_endpoint=None, owner="platform", is_human_actionable=True, mobile_priority="low")]
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
    blocked = _route_blocker_condition()
    row = db.query(
        func.sum(case((blocked, 1), else_=0)).label("blocked"),
        func.sum(case((published & Place.is_route_eligible.is_(False), 1), else_=0)).label("not_route_eligible"),
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


def _route_blocker_condition():
    published = _published_catalog_condition()
    return published & or_(
        Place.is_route_eligible.is_not(True),
        Place.lat.is_(None),
        Place.lng.is_(None),
        _excluded_category_condition(),
        _unknown_category_condition(),
    )


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
