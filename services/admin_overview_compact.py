"""Compact admin overview counts.

This module keeps the interactive overview path on a small number of SQL
statements and aligns card counts with the preset endpoints used for drilldown.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import case, func
from sqlalchemy.orm import Session

from models.admin_audit_log import AdminAuditLog
from models.city import City
from models.city_import_job import CityImportJob
from models.place import Place
from models.place_image import PLACE_IMAGE_STATUS_NEEDS_REVIEW, PlaceImage
from schemas.admin_ops import AdminActionCard, AdminOwner, AdminPrimaryAction, AdminQueueType
from services.admin_backlog_clauses import published_catalog_clause, queue_clause

ACTIVE_IMPORT_STATUSES = ("pending", "running")


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
    counts = _overview_counts(db)
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
        _card("route_blockers", "Проблемы маршрутов", counts["route_blockers"], _sev(counts["route_blockers"], 10, 100), "/admin/places?preset=route_blockers", "Эти места сейчас не попадут в маршруты.", "Открыть проблемы", queue_type="route_blocker", primary_action="open_queue", sample_endpoint="/admin/places/search?preset=route_blockers", owner="data", is_human_actionable=True, mobile_priority="high"),
        _card("not_route_eligible", "Отключены вручную", counts["not_route_eligible"], _sev(counts["not_route_eligible"], 10, 100), "/admin/places?preset=published_not_route_eligible", "Места, явно отключённые от маршрутов.", "Открыть отключённые", queue_type="route_blocker", primary_action="open_queue", sample_endpoint="/admin/places/search?preset=published_not_route_eligible", owner="data", is_human_actionable=True, mobile_priority="medium"),
        _card("route_unknown", "Неизвестные категории", counts["route_unknown"], _sev(counts["route_unknown"], 10, 100), "/admin/places?preset=route_unknown", "Нужно назначить понятную категорию.", "Разобрать категории", queue_type="taxonomy_gap", primary_action="fix_taxonomy", sample_endpoint="/admin/places/search?preset=route_unknown", owner="taxonomy", is_human_actionable=True, mobile_priority="high"),
        _card("route_excluded", "Сервисные точки", counts["route_excluded"], _sev(counts["route_excluded"], 1, 20), "/admin/places?preset=service_places", "Скрыть из маршрутов аптеки, банки, остановки и сервисные POI.", "Открыть сервисные", queue_type="route_blocker", primary_action="open_queue", sample_endpoint="/admin/places/search?preset=service_places", owner="data", is_human_actionable=True, mobile_priority="medium"),
        _card("auto_backlog", "Автоисправление", counts["auto_backlog"], _sev(counts["auto_backlog"], 500, 5000), "/admin/places?preset=auto_backlog", "Очередь для автоматического обогащения и пересчёта.", "Открыть автоочередь", queue_type="auto_fix", primary_action="run_auto_fix", sample_endpoint="/admin/places/search?preset=auto_backlog", owner="automation", is_human_actionable=False, mobile_priority="medium"),
        _card("manual_review", "Ручная проверка", counts["manual_review"], _sev(counts["manual_review"], 20, 100), "/admin/places?preset=manual_review", "Здесь нужны решения оператора.", "Проверить вручную", queue_type="manual_review", primary_action="review_items", sample_endpoint="/admin/places/search?preset=manual_review", owner="content", is_human_actionable=True, mobile_priority="high"),
        _card("needs_verification", "Автоперепроверка", counts["needs_verification"], _sev(counts["needs_verification"], 100, 1000), "/admin/places?preset=needs_verification", "Очередь автоматической проверки данных.", "Открыть очередь", queue_type="verification_backlog", primary_action="run_auto_fix", sample_endpoint="/admin/places/search?preset=needs_verification", owner="automation", is_human_actionable=False, mobile_priority="low"),
        _card("no_photo", "Без фото", counts["no_photo"], _sev(counts["no_photo"], 20, 100), "/admin/places?preset=published_no_photo", "Добавьте фото к опубликованным местам.", "Добавить фото", queue_type="content_gap", primary_action="enrich_content", sample_endpoint="/admin/places/search?preset=published_no_photo", owner="content", is_human_actionable=True, mobile_priority="medium"),
        _card("no_address", "Без адреса", counts["no_address"], _sev(counts["no_address"], 30, 150), "/admin/places?preset=published_no_address", "Уточните адрес для карточек мест.", "Исправить адреса", queue_type="content_gap", primary_action="enrich_content", sample_endpoint="/admin/places/search?preset=published_no_address", owner="content", is_human_actionable=True, mobile_priority="medium"),
        _card("no_description", "Без описания", counts["no_description"], _sev(counts["no_description"], 40, 200), "/admin/places?preset=published_no_description", "Нужно добавить нормальное описание.", "Добавить описания", queue_type="content_gap", primary_action="enrich_content", sample_endpoint="/admin/places/search?preset=published_no_description", owner="content", is_human_actionable=True, mobile_priority="medium"),
        _card("low_confidence", "Низкая уверенность", counts["low_confidence"], _sev(counts["low_confidence"], 15, 80), "/admin/places?preset=published_low_confidence", "Данные места нужно перепроверить.", "Открыть проверку", queue_type="verification_backlog", primary_action="run_auto_fix", sample_endpoint="/admin/places/search?preset=published_low_confidence", owner="automation", is_human_actionable=False, mobile_priority="low"),
    ]
    operations = [_card("cities_total", "Активные города", ops["active_cities"], "green", "/admin/cities", "Города, доступные операторам.", "Открыть города", queue_type="operation", primary_action="open_report", sample_endpoint=None, owner="platform", is_human_actionable=True, mobile_priority="low")]
    return {"critical": critical, "data_quality": data_quality, "operations": operations, "recent_audit_count": ops["audit_recent"], "generated_at": datetime.utcnow()}


def _overview_counts(db: Session) -> dict[str, int]:
    published = published_catalog_clause()
    clauses = {
        "route_blockers": queue_clause("route_blockers"),
        "not_route_eligible": published & Place.is_route_eligible.is_(False),
        "route_unknown": queue_clause("route_unknown"),
        "route_excluded": queue_clause("route_excluded"),
        "auto_backlog": queue_clause("auto_backlog"),
        "manual_review": queue_clause("manual_review"),
        "needs_verification": queue_clause("needs_verification"),
        "no_photo": queue_clause("no_photo"),
        "no_address": queue_clause("no_address"),
        "no_description": queue_clause("no_description"),
        "low_confidence": queue_clause("low_confidence"),
    }
    row = db.query(*[_count_if(clause).label(name) for name, clause in clauses.items()]).one()
    return {name: int(getattr(row, name) or 0) for name in clauses}


def _count_if(clause):
    return func.coalesce(func.sum(case((clause, 1), else_=0)), 0)


def _operational_counts(db: Session) -> dict[str, int]:
    return {
        "pending_photos": _count_query(db.query(func.count(PlaceImage.id)).filter(PlaceImage.status == PLACE_IMAGE_STATUS_NEEDS_REVIEW)),
        "stuck_imports": _count_query(db.query(func.count(CityImportJob.id)).filter(CityImportJob.status.in_(ACTIVE_IMPORT_STATUSES))),
        "active_cities": _count_query(db.query(func.count(City.id)).filter(City.is_active.is_(True), City.launch_status == "published")),
        "audit_recent": _count_query(db.query(func.count(AdminAuditLog.id))),
    }


def _count_query(query) -> int:
    return int(query.scalar() or 0)


def _sev(count: int, yellow: int, red: int) -> str:
    if count >= red:
        return "red"
    if count >= yellow:
        return "yellow"
    return "green"
