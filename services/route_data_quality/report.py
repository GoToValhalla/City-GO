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

P0_MIN_ELIGIBLE_PLACES = 30
P0_MIN_ADDRESS_COVERAGE = 70.0
P0_MIN_PHOTO_COVERAGE = 60.0
P0_MIN_DESCRIPTION_COVERAGE = 50.0


def build_route_data_quality_report(db: Session, *, city_slug: str) -> dict[str, object] | None:
    city = db.query(City).filter(City.slug == city_slug).first()
    if city is None:
        return None
    base = db.query(Place).filter(Place.city_id == city.id)
    total = base.count()
    strict_eligible = base.filter(*route_eligible_sql_conditions()).count()
    with_photo = base.filter(Place.image_url.isnot(None)).count()
    with_address = base.filter(Place.address.isnot(None), Place.address != "").count()
    with_description = base.filter(Place.short_description.isnot(None), Place.short_description != "").count()
    categories = _category_counts(db, city.id)
    buckets = _quality_buckets(db, city.id)
    issues = _issues(db, city, total)
    forbidden_counts = {k: v for k, v in categories.items() if k in ROUTE_FORBIDDEN_CATEGORIES}
    suspicious_counts = {k: v for k, v in categories.items() if k in SUSPICIOUS_CATEGORIES}

    return {
        "city_slug": city.slug,
        "city_name": city.name,
        "places_total": total,
        "places_eligible": strict_eligible,
        "places_not_eligible": max(total - strict_eligible, 0),
        "places_with_photo": with_photo,
        "places_without_photo": max(total - with_photo, 0),
        "places_with_address": with_address,
        "places_without_address": max(total - with_address, 0),
        "places_with_description": with_description,
        "places_without_description": max(total - with_description, 0),
        "category_counts": categories,
        "forbidden_category_counts": forbidden_counts,
        "suspicious_category_counts": suspicious_counts,
        "quality_buckets": buckets,
        "issues": issues,
        "action_plan": _action_plan(
            city_slug=city.slug,
            total=total,
            eligible=strict_eligible,
            with_photo=with_photo,
            with_address=with_address,
            with_description=with_description,
            forbidden_count=sum(forbidden_counts.values()),
            suspicious_count=sum(suspicious_counts.values()),
        ),
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
            "places_link": f"/admin/routes/eligibility?city_slug={city.slug}&issue={code}",
        })
    if total == 0:
        issues.append({"code": "empty_city", "count": 0, "places_link": f"/admin/places?city={city.slug}"})
    return issues


def _action_plan(
    *,
    city_slug: str,
    total: int,
    eligible: int,
    with_photo: int,
    with_address: int,
    with_description: int,
    forbidden_count: int,
    suspicious_count: int,
) -> list[dict[str, object]]:
    """Build a deterministic P0 remediation plan for admin UI and operators.

    The report separates source data problems from route eligibility problems so the admin can
    decide whether to run enrichment, bulk cleanup, or manual review without reading raw metrics.
    """
    actions: list[dict[str, object]] = []

    if total == 0:
        actions.append(_action(
            city_slug,
            code="empty_city",
            severity="blocker",
            title="В городе нет мест",
            count=0,
            recommended_action="Запустить импорт города или проверить seed/import pipeline.",
            issue="empty_city",
        ))
        return actions

    if eligible < P0_MIN_ELIGIBLE_PLACES:
        actions.append(_action(
            city_slug,
            code="low_route_eligible_count",
            severity="blocker",
            title="Недостаточно мест для маршрутов",
            count=eligible,
            recommended_action="Открыть eligibility dashboard, убрать мусорные категории и добавить туристические места.",
            issue="eligible_false",
        ))

    if forbidden_count > 0:
        actions.append(_action(
            city_slug,
            code="exclude_forbidden_categories",
            severity="blocker",
            title="Запрещённые категории попали в маршрутный пул",
            count=forbidden_count,
            recommended_action="Запустить массовое исключение forbidden categories из маршрутов.",
            issue="forbidden_category",
        ))

    if suspicious_count > 0:
        actions.append(_action(
            city_slug,
            code="review_suspicious_categories",
            severity="critical",
            title="Подозрительные категории требуют ревью",
            count=suspicious_count,
            recommended_action="Проверить аптеки, остановки, сервисные точки и выключить лишнее из маршрутов.",
            issue="suspicious_category",
        ))

    address_coverage = _coverage_pct(with_address, total)
    if address_coverage < P0_MIN_ADDRESS_COVERAGE:
        actions.append(_action(
            city_slug,
            code="run_address_recovery",
            severity="critical",
            title="Низкое покрытие адресами",
            count=total - with_address,
            recommended_action="Запустить address recovery flow и применить проверенные результаты.",
            issue="no_address",
        ))

    photo_coverage = _coverage_pct(with_photo, total)
    if photo_coverage < P0_MIN_PHOTO_COVERAGE:
        actions.append(_action(
            city_slug,
            code="run_image_enrichment",
            severity="critical",
            title="Низкое покрытие фотографиями",
            count=total - with_photo,
            recommended_action="Запустить image enrichment/verification и назначить primary images.",
            issue="no_photo",
        ))

    description_coverage = _coverage_pct(with_description, total)
    if description_coverage < P0_MIN_DESCRIPTION_COVERAGE:
        actions.append(_action(
            city_slug,
            code="run_description_enrichment",
            severity="major",
            title="Низкое покрытие описаниями",
            count=total - with_description,
            recommended_action="Запустить enrichment описаний и отправить слабые места на ревью.",
            issue="no_description",
        ))

    return actions


def _action(
    city_slug: str,
    *,
    code: str,
    severity: str,
    title: str,
    count: int,
    recommended_action: str,
    issue: str,
) -> dict[str, object]:
    return {
        "code": code,
        "severity": severity,
        "title": title,
        "count": count,
        "recommended_action": recommended_action,
        "admin_link": f"/admin/routes/eligibility?city_slug={city_slug}&issue={issue}",
    }


def _coverage_pct(value: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(value / total * 100, 1)
