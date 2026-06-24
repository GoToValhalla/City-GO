"""Bounded aggregation layer for admin product analytics."""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from models.product_event import ProductEvent
from models.route_build_event import RouteBuildEvent


def analytics_summary(
    db: Session,
    *,
    days: int = 30,
    city_slug: str | None = None,
    channel: str | None = None,
    region: str | None = None,
    category: str | None = None,
    environment: str | None = None,
) -> dict[str, object]:
    since = datetime.utcnow() - timedelta(days=days)
    city_ids: list[int] | None = None
    if city_slug or region:
        city_query = db.query(City)
        if city_slug:
            city_query = city_query.filter(City.slug == city_slug)
        if region:
            city_query = city_query.filter(City.region == region)
        selected_cities = city_query.all()
        selected_slugs = {city.slug for city in selected_cities}
        city_ids = [city.id for city in selected_cities]
    else:
        selected_slugs = set()
    events = db.query(ProductEvent).filter(ProductEvent.created_at >= since)
    if city_slug:
        events = events.filter(ProductEvent.city_slug == city_slug)
    if region:
        events = events.filter(ProductEvent.city_slug.in_(selected_slugs))
    rows = events.order_by(ProductEvent.created_at.desc()).limit(10000).all()
    if channel:
        rows = [row for row in rows if str((row.payload or {}).get("channel") or "web") == channel]
    if environment:
        rows = [row for row in rows if str((row.payload or {}).get("environment") or "") == environment]
    if category:
        place_ids = {row.id for row in db.query(Place.id).filter(Place.category == category).all()}
        rows = [row for row in rows if row.place_id in place_ids]
    counts = _counts(rows)
    users = {row.user_id for row in rows if row.user_id}
    routes = db.query(RouteBuildEvent).filter(RouteBuildEvent.created_at >= since).all()
    if city_ids is not None:
        allowed_city_ids = {str(value) for value in city_ids}
        routes = [row for row in routes if str(row.city_id or "") in allowed_city_ids]
    success = sum(1 for row in routes if not row.has_warnings)
    places = db.query(Place)
    if city_ids is not None:
        places = places.filter(Place.city_id.in_(city_ids))
    if category:
        places = places.filter(Place.category == category)
    published = places.filter(Place.is_published.is_(True)).count()
    return {
        "period_days": days, "city_slug": city_slug, "channel": channel,
        "region": region, "category": category, "environment": environment,
        "metrics": {
            "active_users": len(users), "events_total": len(rows),
            "place_views": counts.get("place_viewed", 0),
            "place_details": counts.get("place_detail_opened", 0),
            "route_builds": len(routes),
            "route_success_rate": round(success / len(routes) * 100, 1) if routes else None,
            "average_route_points": _average(routes, "total_places"),
            "places_total": places.count(), "places_published": published,
            "published_share": round(published / places.count() * 100, 1) if places.count() else 0,
        },
        "event_breakdown": [{"event": key, "count": value} for key, value in sorted(counts.items())],
        "availability": {
            "dau_wau_mau": bool(users),
            "funnels": bool(counts.get("place_viewed") and counts.get("route_generation_success")),
            "comparison": False,
        },
    }


def _counts(rows: list[ProductEvent]) -> dict[str, int]:
    result: dict[str, int] = {}
    for row in rows:
        result[row.event_type] = result.get(row.event_type, 0) + 1
    return result


def _average(rows: list[RouteBuildEvent], field: str) -> float | None:
    values = [float(getattr(row, field)) for row in rows]
    return round(sum(values) / len(values), 1) if values else None
