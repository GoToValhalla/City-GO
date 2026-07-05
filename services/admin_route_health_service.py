from __future__ import annotations

from collections import Counter
from datetime import datetime

from sqlalchemy.orm import Session, joinedload

from models.city import City
from models.route import Route
from models.route_place import RoutePlace
from services.route_eligibility_policy import HARD_EXCLUDED_CATEGORIES, evaluate_place_route_eligibility
from schemas.admin_route_health import RouteHealthIssue, RouteHealthSummary

MIN_TOURIST_POINTS = 3
LONG_TRANSITION_KM_WARNING = 5.0


def build_route_health_summary(db: Session, *, city_slug: str | None = None) -> RouteHealthSummary:
    city_id: int | None = None
    if city_slug:
        city = db.query(City).filter(City.slug == city_slug).one_or_none()
        if city is None:
            raise LookupError("Город не найден")
        city_id = city.id

    query = db.query(Route).options(joinedload(Route.route_places).joinedload(RoutePlace.place))
    if city_id is not None:
        query = query.filter(Route.city_id == city_id)
    routes = query.order_by(Route.id.asc()).limit(200).all()

    issues: list[RouteHealthIssue] = []
    for route in routes:
        route_places = sorted(route.route_places, key=lambda item: item.position)
        places = [item.place for item in route_places if item.place is not None]
        tourist_places = [place for place in places if evaluate_place_route_eligibility(place).eligible]

        if len(tourist_places) < MIN_TOURIST_POINTS:
            issues.append(_issue(
                route,
                "route_min_points_failed",
                "Маршрут содержит меньше 3 туристических точек",
                "critical",
                {"tourist_points": len(tourist_places), "minimum": MIN_TOURIST_POINTS},
            ))

        service_places = []
        for place in places:
            category = (place.canonical_category or place.category or "").strip().lower()
            if category in HARD_EXCLUDED_CATEGORIES or not evaluate_place_route_eligibility(place).eligible:
                service_places.append({"id": place.id, "title": place.title, "category": category or "unknown"})
        if service_places:
            issues.append(_issue(
                route,
                "route_service_places_detected",
                "Маршрут содержит служебные или непригодные для прогулки места",
                "critical",
                {"places": service_places[:10], "total": len(service_places)},
            ))

        mixed_city_places = [place.id for place in places if place.city_id != route.city_id]
        if mixed_city_places:
            issues.append(_issue(
                route,
                "route_city_mixing_error",
                "Маршрут содержит точки из другого города",
                "critical",
                {"place_ids": mixed_city_places},
            ))

        if (route.distance_km or 0.0) > LONG_TRANSITION_KM_WARNING and len(places) <= 2:
            issues.append(_issue(
                route,
                "route_long_transition_warning",
                "Маршрут содержит слишком длинный переход без промежуточных точек",
                "warning",
                {"distance_km": route.distance_km},
            ))

        category_counts = Counter((place.canonical_category or place.category or "unknown") for place in tourist_places)
        if len(tourist_places) >= 4 and category_counts and max(category_counts.values()) >= len(tourist_places) - 1:
            issues.append(_issue(
                route,
                "route_low_diversity_warning",
                "Маршрут почти полностью состоит из одной категории мест",
                "warning",
                {"categories": dict(category_counts)},
            ))

    critical = sum(1 for issue in issues if issue.severity == "critical")
    warning = sum(1 for issue in issues if issue.severity == "warning")
    status = "critical" if critical else "warning" if warning else "healthy"
    return RouteHealthSummary(
        city_slug=city_slug,
        checked_at=datetime.utcnow(),
        routes_checked=len(routes),
        critical_count=critical,
        warning_count=warning,
        status=status,
        issues=issues,
    )


def _issue(route: Route, code: str, label: str, severity: str, details: dict[str, object]) -> RouteHealthIssue:
    return RouteHealthIssue(
        code=code,
        label=label,
        severity=severity,  # type: ignore[arg-type]
        route_id=route.id,
        route_title=route.title,
        details=details,
    )
