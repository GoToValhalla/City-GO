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
    rows = [city_quality_row(db, city, category) for city in cities.order_by(City.name).all()]
    filtered = [row for row in rows if not severity or row["severity"] == severity]
    return {
        "items": filtered,
        "total": len(filtered),
        "todo": [
            "Главный экран качества теперь показывает live score, а не устаревшее поле City.readiness_score.",
            "Следующий шаг: вынести breakdown в CityQualitySnapshot с историей по дням.",
            "Следующий шаг: добавить отдельную очередь possible_duplicate для ручного merge/reject.",
        ],
    }


def city_quality_row(db: Session, city: City, category: str | None = None) -> dict[str, object]:
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
    score = _live_quality_score(total, blockers)
    severity = "critical" if score < 40 else "warning" if score < 75 else "ok"
    return {
        "city_slug": city.slug,
        "city_name": city.name,
        "region": city.region,
        "readiness_score": score,
        "stored_readiness_score": int(city.readiness_score or 0),
        "places_total": total,
        "severity": severity,
        "blockers": blockers,
        "primary_blocker": _primary_blocker(blockers),
    }


def _city_row(db: Session, city: City, category: str | None) -> dict[str, object]:
    return city_quality_row(db, city, category)


def _live_quality_score(total: int, blockers: dict[str, int]) -> int:
    if total <= 0:
        return 0
    penalty = (
        35 * _ratio(blockers["no_photo"], total)
        + 25 * _ratio(blockers["no_address"], total)
        + 20 * _ratio(blockers["low_quality"], total)
        + 10 * _ratio(blockers["stale"], total)
    )
    # route_ineligible is shown as an operational count but is not a penalty:
    # excluding pharmacies/banks/services from routes is often the correct state.
    return max(0, min(100, round(100 - penalty)))


def _ratio(value: int, total: int) -> float:
    return min(1.0, max(0.0, value / total)) if total else 0.0


def _primary_blocker(blockers: dict[str, int]) -> str | None:
    candidates = {key: value for key, value in blockers.items() if key != "route_ineligible" and value > 0}
    if not candidates:
        return None
    return max(candidates, key=candidates.get)
