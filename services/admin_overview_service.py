"""Обзор админки: actionable cards «что требует внимания»."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from models.admin_audit_log import AdminAuditLog
from models.city import City
from models.city_import_job import CityImportJob
from models.place import Place
from models.place_image import PLACE_IMAGE_STATUS_NEEDS_REVIEW, PlaceImage
from schemas.admin_ops import AdminActionCard


def _card(code: str, title: str, count: int, severity: str, link_path: str, hint: str | None = None) -> AdminActionCard:
    return AdminActionCard(code=code, title=title, count=count, severity=severity, link_path=link_path, hint=hint)


def build_admin_overview(db: Session) -> dict[str, object]:
    no_photo = db.query(Place).filter(Place.image_url.is_(None), Place.is_published.is_(True)).count()
    no_addr = db.query(Place).filter(Place.address.is_(None), Place.is_published.is_(True)).count()
    no_desc = db.query(Place).filter(Place.short_description.is_(None), Place.is_published.is_(True)).count()
    low_conf = db.query(Place).filter(Place.existence_confidence_level.in_(("low", "unknown")), Place.is_published.is_(True)).count()
    needs_review = db.query(Place).filter(Place.verification_status.in_(("needs_recheck", "unverified"))).count()
    not_route = db.query(Place).filter(Place.is_route_eligible.is_(False), Place.is_published.is_(True)).count()
    pending_photos = db.query(PlaceImage).filter(PlaceImage.status == PLACE_IMAGE_STATUS_NEEDS_REVIEW).count()
    stuck_imports = db.query(CityImportJob).filter(CityImportJob.status.in_(("pending", "running"))).count()
    cities_weak = db.query(City).filter(City.is_active.is_(True)).count()
    audit_recent = db.query(AdminAuditLog).count()
    critical = [c for c in [
        _card("pending_photos", "Фото на модерации", pending_photos, "red" if pending_photos else "green", "/admin/photos"),
        _card("stuck_imports", "Зависшие импорты", stuck_imports, "yellow" if stuck_imports else "green", "/admin/imports"),
    ] if c.count > 0 or c.code == "pending_photos"]
    data_quality = [
        _card("no_photo", "Опубликовано без фото", no_photo, _sev(no_photo, 20, 100), "/admin/places?preset=no_photo"),
        _card("no_address", "Без адреса", no_addr, _sev(no_addr, 30, 150), "/admin/places?preset=no_address"),
        _card("no_description", "Без описания", no_desc, _sev(no_desc, 40, 200), "/admin/places?preset=no_description"),
        _card("low_confidence", "Низкая уверенность", low_conf, _sev(low_conf, 15, 80), "/admin/places?preset=low_confidence"),
        _card("needs_verification", "Требуют проверки", needs_review, _sev(needs_review, 20, 100), "/admin/verification"),
        _card("not_route_eligible", "Исключены из маршрутов", not_route, "yellow" if not_route else "green", "/admin/places?preset=not_in_routes"),
    ]
    operations = [_card("cities_total", "Активных городов", cities_weak, "green", "/admin/cities")]
    return {"critical": critical, "data_quality": data_quality, "operations": operations, "recent_audit_count": audit_recent, "generated_at": datetime.utcnow()}


def _sev(count: int, yellow: int, red: int) -> str:
    if count >= red:
        return "red"
    if count >= yellow:
        return "yellow"
    return "green"
