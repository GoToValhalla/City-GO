"""System health aggregation from persisted operational signals."""

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.city_admin_import_job import CityAdminImportJob
from models.place_image import PlaceImage
from models.review_queue_item import ReviewQueueItem
from models.route_build_event import RouteBuildEvent
from models.system_log import SystemLog


def health_summary(db: Session) -> dict[str, object]:
    log_rows = db.query(SystemLog).order_by(SystemLog.created_at.desc()).limit(200).all()
    latest_logs = {
        row.module: row for row in reversed(log_rows)
    }
    stalled = _count(db, CityAdminImportJob, CityAdminImportJob.status == "stalled")
    queues = {
        "imports": _count(db, CityAdminImportJob, CityAdminImportJob.status.in_(("queued", "running"))),
        "verification": _count(db, ReviewQueueItem, ReviewQueueItem.status == "open"),
        "photos": _count(db, PlaceImage, PlaceImage.status == "needs_review"),
    }
    route_rows = db.query(RouteBuildEvent).order_by(RouteBuildEvent.created_at.desc()).limit(500).all()
    routes = len(route_rows)
    route_latency = _percentile([row.latency_ms for row in route_rows], 95)
    route_errors = sum(1 for row in route_rows if row.has_warnings)
    services = [
        _service("API", "ok", "Запрос health center выполнен."),
        _service("База данных", "ok", "Агрегирующий запрос выполнен."),
        _service("Импорт", "error" if stalled else "ok", f"Зависших задач: {stalled}", queues["imports"]),
        _service("Обогащение", _module_status(latest_logs, "enrichment"), "Последнее событие обогащения."),
        _service("Фото", "warning" if queues["photos"] else "ok", "Очередь проверки фото.", queues["photos"]),
        _service(
            "Маршруты", "ok" if routes else "unknown", f"Сборок зарегистрировано: {routes}",
            latency=route_latency, error_rate=round(route_errors / routes * 100, 1) if routes else None,
        ),
        _service("Telegram", _module_status(latest_logs, "telegram"), "Состояние по последнему логу."),
        _service("Очередь проверки", "warning" if queues["verification"] else "ok", "Полевые проверки.", queues["verification"]),
    ]
    return {"generated_at": datetime.utcnow(), "services": services, "queues": queues, "retention_days": 30}


def _service(
    name: str, status: str, description: str, queue: int = 0,
    latency: int | None = None, error_rate: float | None = None,
) -> dict[str, object]:
    return {
        "name": name, "status": status, "description": description,
        "queue_depth": queue, "latency_ms": latency, "error_rate": error_rate,
        "stale_threshold_minutes": 30,
    }


def _module_status(logs: dict[str, SystemLog], prefix: str) -> str:
    rows = [row for key, row in logs.items() if prefix in key]
    if not rows:
        return "unknown"
    return "error" if rows[0].level in {"error", "critical"} else "ok"


def _count(db: Session, model, *filters) -> int:
    return int(db.query(func.count(model.id)).filter(*filters).scalar() or 0)


def _percentile(values: list[int], percentile: int) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(round((percentile / 100) * (len(ordered) - 1)), len(ordered) - 1)
    return int(ordered[index])
