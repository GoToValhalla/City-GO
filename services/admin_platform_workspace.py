"""City workspace operational aggregates."""

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.admin_audit_log import AdminAuditLog
from models.city import City
from models.data_quality import DataQualityIssue
from models.place import Place
from models.place_image import PlaceImage
from models.review_queue_item import ReviewQueueItem
from models.route import Route
from models.system_log import SystemLog
from services.data_quality.constants import ISSUE_POSSIBLE_DUPLICATE, OPEN_STATUSES


def workspace_operations(db: Session, city: City) -> dict[str, object]:
    places = db.query(Place).filter(Place.city_id == city.id)
    open_review = _count(db, ReviewQueueItem, ReviewQueueItem.city_id == city.id, ReviewQueueItem.status == "open")
    pending_photos = int(
        db.query(func.count(PlaceImage.id)).join(Place).filter(
            Place.city_id == city.id, PlaceImage.status == "needs_review",
        ).scalar() or 0
    )
    quality_counts = _quality_counts(places)
    quality_counts["possible_duplicates"] = _open_duplicate_issues(db, city.id)
    errors = db.query(SystemLog).filter(SystemLog.city_slug == city.slug).order_by(SystemLog.created_at.desc()).limit(5).all()
    audit_candidates = db.query(AdminAuditLog).order_by(AdminAuditLog.created_at.desc()).limit(100).all()
    audits = [row for row in audit_candidates if _matches_city(row, city)][:5]
    return {
        "quality": quality_counts,
        "queues": {"verification": open_review, "photos": pending_photos},
        "routes": {
            "published": _count(db, Route, Route.city_id == city.id, Route.is_active.is_(True)),
            "total": _count(db, Route, Route.city_id == city.id),
            "eligible_places": places.filter(Place.is_route_eligible.is_(True)).count(),
        },
        "critical_issues": sum(quality_counts.values()),
        "active_operations": open_review + pending_photos,
        "recent_errors": [_log_row(row) for row in errors],
        "recent_audit": [_audit_row(row) for row in audits],
    }


def _quality_counts(query) -> dict[str, int]:
    return {
        "no_photo": query.filter(Place.image_url.is_(None)).count(),
        "no_address": query.filter(Place.address.is_(None)).count(),
        "no_description": query.filter(Place.short_description.is_(None)).count(),
        "no_hours": query.filter(Place.opening_hours.is_(None)).count(),
        "low_quality": query.filter(Place.quality_score < 50).count(),
        "route_ineligible": query.filter(Place.is_route_eligible.is_(False)).count(),
    }


def _open_duplicate_issues(db: Session, city_id: int) -> int:
    return int(
        db.query(func.count(DataQualityIssue.id))
        .filter(
            DataQualityIssue.city_id == city_id,
            DataQualityIssue.issue_type == ISSUE_POSSIBLE_DUPLICATE,
            DataQualityIssue.status.in_(OPEN_STATUSES),
        )
        .scalar() or 0
    )


def _count(db: Session, model, *filters) -> int:
    return int(db.query(func.count(model.id)).filter(*filters).scalar() or 0)


def _log_row(row: SystemLog) -> dict[str, object]:
    return {"id": row.id, "level": row.level, "module": row.module, "message": row.message, "created_at": row.created_at}


def _audit_row(row: AdminAuditLog) -> dict[str, object]:
    return {"id": row.id, "actor": row.actor, "action": row.action, "entity_type": row.entity_type, "created_at": row.created_at}


def _matches_city(row: AdminAuditLog, city: City) -> bool:
    payloads = (row.old_value or {}, row.new_value or {})
    return any(str(payload.get("city_slug") or "") == city.slug or payload.get("city_id") == city.id for payload in payloads)
