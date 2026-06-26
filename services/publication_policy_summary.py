from __future__ import annotations

from collections import Counter
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

    failed_gate_counts, review_reason_counts, recent_blocked = _decision_reasons(decisions_query)

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
        "top_failed_gates": failed_gate_counts,
        "top_review_reasons": review_reason_counts,
        "recent_blocked": recent_blocked,
        "cities": sorted(by_city.values(), key=lambda item: (-int(item["total"]), str(item["slug"]))),
        "open_publication_review_items": open_review_query.count(),
        "pending_change_reviews": pending_change_query.count(),
    }


def _decision_reasons(decisions_query) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    failed_gates: Counter[str] = Counter()
    review_reasons: Counter[str] = Counter()
    recent_blocked: list[dict[str, object]] = []

    rows = decisions_query.join(City, City.id == PlacePublicationDecision.city_id).with_entities(
        PlacePublicationDecision.decision,
        PlacePublicationDecision.trust_score,
        PlacePublicationDecision.failed_gates,
        PlacePublicationDecision.review_reasons,
        PlacePublicationDecision.payload,
        City.slug,
        City.name,
    ).order_by(PlacePublicationDecision.created_at.desc()).limit(500).all()

    for decision, trust_score, gates, reasons, payload, city_slug, city_name in rows:
        gates = list(gates or [])
        reasons = list(reasons or [])
        failed_gates.update(gates)
        review_reasons.update(reasons)
        if decision in {"hidden", "send_to_review"} and len(recent_blocked) < 8:
            recent_blocked.append({
                "decision": decision,
                "city_slug": city_slug,
                "city_name": city_name,
                "title": (payload or {}).get("title"),
                "trust_score": trust_score,
                "failed_gates": gates,
                "review_reasons": reasons,
            })

    return _counter_payload(failed_gates), _counter_payload(review_reasons), recent_blocked


def _counter_payload(counter: Counter[str]) -> list[dict[str, object]]:
    return [{"reason": reason, "count": count} for reason, count in counter.most_common(8)]


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

    _append_reason_lines(lines, "ПРИЧИНЫ REVIEW", summary.get("top_review_reasons") or [])
    _append_reason_lines(lines, "FAILED GATES", summary.get("top_failed_gates") or [])

    blocked = summary.get("recent_blocked") or []
    if blocked:
        lines.extend(["", "ПОСЛЕДНИЕ BLOCKED"])
        for item in blocked[:5]:
            reasons = ", ".join(item.get("review_reasons") or item.get("failed_gates") or []) or "no_reason"
            lines.append(f"{item.get('city_name') or item.get('city_slug')}: {item.get('title') or 'без названия'} · score {item.get('trust_score')} · {reasons}")

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


def _append_reason_lines(lines: list[str], title: str, reasons: list[dict[str, object]]) -> None:
    if not reasons:
        return
    lines.extend(["", title])
    for item in reasons[:5]:
        lines.append(f"{item.get('reason')}: {item.get('count')}")
