"""Cross-city quality dashboard aggregate."""

from sqlalchemy.orm import Session

from models.city import City
from models.place import Place


def quality_summary(
    db: Session,
    *,
    city_slug: str | None = None,
    region: str | None = None,
    category: str | None = None,
    severity: str | None = None,
) -> dict[str, object]:
    cities = db.query(City)
    if city_slug:
        cities = cities.filter(City.slug == city_slug)
    if region:
        cities = cities.filter(City.region == region)
    rows = [_city_row(db, city, category) for city in cities.order_by(City.name).all()]
    filtered = [row for row in rows if not severity or row["severity"] == severity]
    return {
        "items": filtered,
        "total": len(filtered),
        "todo": [
            "Модель: ежедневный CityQualitySnapshot с breakdown по категории и severity.",
            "Endpoint: GET /admin/quality/history с периодом и группировкой.",
            "Алгоритм: materialized daily aggregate без повторного подсчёта мест.",
            "Индексы: city_id, category, severity, snapshot_date.",
            "Фоновая задача: nightly snapshot и пересчёт после массовых действий.",
            "Тесты: история, идемпотентность snapshot, timezone boundary.",
            "Готовность: 30 дней данных, p95 ответа менее 500 мс, сверка с live count.",
        ],
    }


def _city_row(db: Session, city: City, category: str | None) -> dict[str, object]:
    query = db.query(Place).filter(Place.city_id == city.id)
    if category:
        query = query.filter(Place.category == category)
    total = query.count()
    blockers = {
        "no_photo": query.filter(Place.image_url.is_(None)).count(),
        "no_address": query.filter(Place.address.is_(None)).count(),
        "low_quality": query.filter(Place.quality_score < 50).count(),
        "stale": query.filter(Place.verification_status == "needs_recheck").count(),
        "route_ineligible": query.filter(Place.is_route_eligible.is_(False)).count(),
    }
    score = int(city.readiness_score or 0)
    severity = "critical" if score < 40 else "warning" if score < 75 else "ok"
    return {
        "city_slug": city.slug, "city_name": city.name, "region": city.region,
        "readiness_score": score, "places_total": total, "severity": severity, "blockers": blockers,
    }
