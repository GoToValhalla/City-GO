"""Route Data Quality отчёт по городу."""

from __future__ import annotations

from collections import Counter

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from services.place_quality_score import compute_place_quality_score, quality_bucket
from services.route_eligibility import ROUTE_FORBIDDEN_CATEGORIES, route_eligible_sql_conditions
from services.route_eligibility_dashboard.reasons import dashboard_reasons

SUSPICIOUS_CATEGORIES = frozenset({
    "pharmacy", "bus_stop", "transport", "useful", "service", "health",
})


def build_route_data_quality_report(db: Session, *, city_slug: str) -> dict[str, object] | None:
    city = db.query(City).filter(City.slug == city_slug).first()
    if city is None:
        return None
    base = db.query(Place).filter(Place.city_id == city.id)
    total = base.count()
    strict_eligible = base.filter(*route_eligible_sql_conditions()).count()
    categories = _category_counts(db, city.id)
    buckets = _quality_buckets(db, city.id)
    return {
        "city_slug": city.slug,
        "city_name": city.name,
        "places_total": total,
        "places_eligible": strict_eligible,
        "places_not_eligible": max(total - strict_eligible, 0),
        "places_with_photo": base.filter(Place.image_url.isnot(None)).count(),
        "places_without_photo": base.filter(Place.image_url.is_(None)).count(),
        "places_with_address": base.filter(Place.address.isnot(None), Place.address != "").count(),
        "places_without_address": base.filter(or_(Place.address.is_(None), Place.address == "")).count(),
        "places_with_description": base.filter(Place.short_description.isnot(None), Place.short_description != "").count(),
        "places_without_description": base.filter(or_(Place.short_description.is_(None), Place.short_description == "")).count(),
        "category_counts": categories,
        "forbidden_category_counts": {k: v for k, v in categories.items() if k in ROUTE_FORBIDDEN_CATEGORIES},
        "suspicious_category_counts": {k: v for k, v in categories.items() if k in SUSPICIOUS_CATEGORIES},
        "quality_buckets": buckets,
        "issues": _issues(db, city, total),
    }


def _category_counts(db: Session, city_id: int) -> dict[str, int]:
    rows = db.execute(
        select(Place.category, func.count(Place.id)).where(Place.city_id == city_id).group_by(Place.category),
    ).all()
    return {str(cat or "unknown"): int(cnt) for cat, cnt in rows}


def _quality_buckets(db: Session, city_id: int) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for place in db.query(Place).filter(Place.city_id == city_id).limit(2000).all():
        counter[quality_bucket(compute_place_quality_score(place))] += 1
    return dict(counter)


def _issues(db: Session, city: City, total: int) -> list[dict[str, object]]:
    base = db.query(Place).filter(Place.city_id == city.id)
    defs = [
        ("no_photo", base.filter(Place.image_url.is_(None))),
        ("no_address", base.filter(or_(Place.address.is_(None), Place.address == ""))),
        ("no_description", base.filter(or_(Place.short_description.is_(None), Place.short_description == ""))),
        ("no_coordinates", base.filter(or_(Place.lat.is_(None), Place.lng.is_(None)))),
        ("forbidden_category", base.filter(Place.category.in_(tuple(ROUTE_FORBIDDEN_CATEGORIES)))),
        ("suspicious_category", base.filter(Place.category.in_(tuple(SUSPICIOUS_CATEGORIES)))),
        ("low_quality", None),
    ]
    issues: list[dict[str, object]] = []
    for code, query in defs:
        if code == "low_quality":
            count = sum(
                1 for p in base.limit(500).all()
                if "low_quality" in dashboard_reasons(p, city=city)
            )
        else:
            count = query.count() if query is not None else 0
        issues.append({
            "code": code,
            "count": count,
            "places_link": f"/admin/routes/eligibility?city={city.slug}&issue={code}",
        })
    if total == 0:
        issues.append({"code": "empty_city", "count": 0, "places_link": f"/admin/places?city={city.slug}"})
    return issues
