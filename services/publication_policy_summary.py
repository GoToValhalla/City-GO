from __future__ import annotations

from datetime import datetime, timedelta
from statistics import mean
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.city import City
from models.place_change_review import PlaceChangeReview
from models.place_publication_decision import PlacePublicationDecision
from models.review_queue_item import ReviewQueueItem

PUBLICATION_REVIEW_REASONS = {
    "NEW_PLACE",
    "LOW_TRUST_SCORE",
    "HARD_GATE_FAILED",
    "DUPLICATE_SUSPICION",
    "SUSPICIOUS_CONTENT",
    "CRITICAL_FIELD_CHANGED",
    "NAME_CHANGE",
    "CATEGORY_CHANGE",
    "LOCATION_CHANGE",
    "ADDRESS_CHANGE",
    "CLOSURE",
}


def get_publication_policy_summary(
    db: Session,
    *,
    days: int = 7,
    city_slug: str | None = None,
) -> dict[str, Any]:
    days = max(1, min(days, 90))
    since = datetime.utcnow() - timedelta(days=days)

    decisions_query = db.query(PlacePublicationDecision).filter(PlacePublicationDecision.created_at >= since)
    if city_slug:
        decisions_query = decisions_query.join(City, City.id == PlacePublicationDecision.city_id).filter(City.slug == city_slug)

    grouped_rows = decisions_query.with_entities(
        PlacePublicationDecision.mode,
        PlacePublicationDecision.decision,
        func.count(PlacePublicationDecision.id),
    ).group_by(PlacePublicationDecision.mode, PlacePublicationDecision.decision).all()

    by_mode: dict[str, dict[str, int]] = {}
    by_decision: dict[str, int] = {}
    for mode, decision, count in grouped_rows:
        count = int(count or 0)
        by_mode.setdefault(mode, {})[decision] = count
        by_decision[decision] = by_decision.get(decision, 0) + count

    score_rows = decisions_query.with_entities(PlacePublicationDecision.trust_score).all()
    scores = [float(row[0]) for row in score_rows if row[0] is not None]

    city_rows = decisions_query.join(City, City.id == PlacePublicationDecision.city_id).with_entities(
        City.slug,
        City.name,
        PlacePublicationDecision.decision,
        func.count(PlacePublicationDecision.id),
    ).group_by(City.slug, City.name, PlacePublicationDecision.decision).all()
    by_city: dict[str, dict[str, Any]] = {}
    for slug, name, decision, count in city_rows:
        payload = by_city.setdefault(slug, {"slug": slug, "name": name, "total": 0, "decisions": {}})
        payload["decisions"][decision] = int(count or 0)
        payload["total"] += int(count or 0)

    open_review_query = db.query(ReviewQueueItem).filter(
        ReviewQueueItem.status == "open",
        ReviewQueueItem.reason.in_(tuple(PUBLICATION_REVIEW_REASONS)),
    )
    pending_change_query = db.query(PlaceChangeReview).filter(PlaceChangeReview.status == "pending")
    if city_slug:
        open_review_query = open_review_query.join(City, City.id == ReviewQueueItem.city_id).filter(City.slug == city_slug)
        pending_change_query = pending_change_query.join(City, City.id == PlaceChangeReview.city_id).filter(City.slug == city_slug)

    return {
        "period_days": days,
        "since": since.isoformat(timespec="seconds") + "Z",
        "city_slug": city_slug,
        "total_decisions": sum(by_decision.values()),
        "by_decision": by_decision,
        "by_mode": by_mode,
        "trust_score": {
            "avg": round(mean(scores), 2) if scores else None,
            "min": min(scores) if scores else None,
            "max": max(scores) if scores else None,
        },
        "cities": sorted(by_city.values(), key=lambda item: (-int(item["total"]), str(item["slug"]))),
        "open_publication_review_items": open_review_query.count(),
        "pending_change_reviews": pending_change_query.count(),
    }


def format_publication_policy_summary(summary: dict[str, Any], *, run_url: str | None = None, status: str = "success") -> str:
    status_line = "✅ пройден" if status == "success" else "❌ не пройден"
    by_decision = summary.get("by_decision") or {}
    trust = summary.get("trust_score") or {}
    cities = summary.get("cities") or []
    city_scope = summary.get("city_slug") or "все города"

    lines = [
        "CITY GO · PUBLICATION POLICY",
        f"Статус: {status_line}",
        f"Период статистики: {summary.get('period_days')} дн. · область: {city_scope}",
        "",
        "РЕШЕНИЯ",
        f"Всего: {summary.get('total_decisions', 0)}",
        f"Shadow auto: {by_decision.get('shadow_auto_publish', 0)}",
        f"Auto published: {by_decision.get('auto_publish', 0)}",
        f"Review: {by_decision.get('send_to_review', 0)}",
        f"Hidden: {by_decision.get('hidden', 0)}",
        "",
        "КАЧЕСТВО",
        f"Trust score avg/min/max: {trust.get('avg')}/{trust.get('min')}/{trust.get('max')}",
        f"Открыто publication review: {summary.get('open_publication_review_items', 0)}",
        f"Открыто change review: {summary.get('pending_change_reviews', 0)}",
    ]

    if cities:
        lines.extend(["", "ГОРОДА"])
        for city in cities[:8]:
            decisions = city.get("decisions") or {}
            lines.append(
                f"{city.get('name') or city.get('slug')}: всего {city.get('total', 0)} · "
                f"auto {decisions.get('auto_publish', 0)} · shadow {decisions.get('shadow_auto_publish', 0)} · "
                f"review {decisions.get('send_to_review', 0)} · hidden {decisions.get('hidden', 0)}"
            )

    if run_url:
        lines.extend(["", f"GitHub Actions: {run_url}"])
    return "\n".join(lines)
