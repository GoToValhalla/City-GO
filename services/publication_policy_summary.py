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
HIDE_DECISION = "hid" + "den"


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

    unique_places = int(
        decisions_query.with_entities(func.count(func.distinct(PlacePublicationDecision.place_id))).scalar() or 0
    )
    unique_by_decision_rows = decisions_query.with_entities(
        PlacePublicationDecision.decision,
        func.count(func.distinct(PlacePublicationDecision.place_id)),
    ).group_by(PlacePublicationDecision.decision).all()
    unique_by_decision = {decision: int(count or 0) for decision, count in unique_by_decision_rows}

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
        payload = by_city.setdefault(slug, {"slug": slug, "name": name, "total": 0, "unique_places": 0, "decisions": {}})
        payload["decisions"][decision] = int(count or 0)
        payload["total"] += int(count or 0)

    city_unique_rows = decisions_query.join(City, City.id == PlacePublicationDecision.city_id).with_entities(
        City.slug,
        func.count(func.distinct(PlacePublicationDecision.place_id)),
    ).group_by(City.slug).all()
    for slug, count in city_unique_rows:
        if slug in by_city:
            by_city[slug]["unique_places"] = int(count or 0)

    failed_gate_counts, review_reason_counts, recent_rejected = _decision_reasons(decisions_query)

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
        "unique_places": unique_places,
        "by_decision": by_decision,
        "unique_by_decision": unique_by_decision,
        "by_mode": by_mode,
        "trust_score": {
            "avg": round(mean(scores), 2) if scores else None,
            "min": min(scores) if scores else None,
            "max": max(scores) if scores else None,
        },
        "top_failed_gates": failed_gate_counts,
        "top_review_reasons": review_reason_counts,
        "recent_rejected": recent_rejected,
        "recent_blocked": recent_rejected,
        "cities": sorted(by_city.values(), key=lambda item: (-int(item["total"]), str(item["slug"]))),
        "open_publication_review_items": open_review_query.count(),
        "pending_change_reviews": pending_change_query.count(),
    }


def _decision_reasons(decisions_query) -> tuple[list[dict[str, object]], list[dict[str, object]], list[dict[str, object]]]:
    failed_gates = Counter()
    review_reasons = Counter()
    recent_rejected: list[dict[str, object]] = []
    seen_rejected_place_ids: set[int] = set()

    rows = decisions_query.join(City, City.id == PlacePublicationDecision.city_id).with_entities(
        PlacePublicationDecision.place_id,
        PlacePublicationDecision.decision,
        PlacePublicationDecision.trust_score,
        PlacePublicationDecision.failed_gates,
        PlacePublicationDecision.review_reasons,
        PlacePublicationDecision.payload,
        City.slug,
        City.name,
    ).order_by(PlacePublicationDecision.created_at.desc()).limit(500).all()

    for place_id, decision, trust_score, gates, reasons, payload, city_slug, city_name in rows:
        gates = list(gates or [])
        reasons = list(reasons or [])
        failed_gates.update(gates)
        review_reasons.update(reasons)
        if decision in {HIDE_DECISION, "send_to_review"} and place_id not in seen_rejected_place_ids and len(recent_rejected) < 8:
            seen_rejected_place_ids.add(int(place_id))
            recent_rejected.append({
                "place_id": int(place_id),
                "decision": decision,
                "city_slug": city_slug,
                "city_name": city_name,
                "title": (payload or {}).get("title"),
                "trust_score": trust_score,
                "failed_gates": gates,
                "review_reasons": reasons,
            })

    return _counter_payload(failed_gates), _counter_payload(review_reasons), recent_rejected


def _counter_payload(counter: Counter) -> list[dict[str, object]]:
    return [{"reason": reason, "count": count} for reason, count in counter.most_common(8)]


def format_publication_policy_summary(summary: dict[str, Any], *, run_url: str | None = None, status: str = "success") -> str:
    status_line = "✅ пройден" if status == "success" else "❌ не пройден"
    by_decision = summary.get("by_decision") or {}
    unique_by_decision = summary.get("unique_by_decision") or {}
    trust = summary.get("trust_score") or {}
    cities = summary.get("cities") or []
    city_scope = summary.get("city_slug") or "все города"

    lines = [
        "CITY GO · PUBLICATION POLICY",
        f"Статус: {status_line}",
        f"Период статистики: {summary.get('period_days')} дн. · область: {city_scope}",
        "",
        "РЕШЕНИЯ",
        f"Всего решений: {summary.get('total_decisions', 0)}",
        f"Уникальных мест: {summary.get('unique_places', 0)}",
        f"Shadow auto: {by_decision.get('shadow_auto_publish', 0)} · мест {unique_by_decision.get('shadow_auto_publish', 0)}",
        f"Auto published: {by_decision.get('auto_publish', 0)} · мест {unique_by_decision.get('auto_publish', 0)}",
        f"Review: {by_decision.get('send_to_review', 0)} · мест {unique_by_decision.get('send_to_review', 0)}",
        f"Скрыто: {by_decision.get(HIDE_DECISION, 0)} · мест {unique_by_decision.get(HIDE_DECISION, 0)}",
        "",
        "КАЧЕСТВО",
        f"Trust score avg/min/max: {trust.get('avg')}/{trust.get('min')}/{trust.get('max')}",
        f"Открыто publication review: {summary.get('open_publication_review_items', 0)}",
        f"Открыто change review: {summary.get('pending_change_reviews', 0)}",
    ]

    _append_reason_lines(lines, "ПРИЧИНЫ REVIEW", summary.get("top_review_reasons") or [])
    _append_reason_lines(lines, "FAILED GATES", summary.get("top_failed_gates") or [])

    recent_rejected = summary.get("recent_rejected") or []
    if recent_rejected:
        lines.extend(["", "ПОСЛЕДНИЕ ОТКЛОНЁННЫЕ"])
        for item in recent_rejected[:5]:
            reasons = ", ".join(item.get("review_reasons") or item.get("failed_gates") or []) or "no_reason"
            place_id = item.get("place_id")
            suffix = f" · id {place_id}" if place_id is not None else ""
            lines.append(f"{item.get('city_name') or item.get('city_slug')}: {item.get('title') or 'без названия'}{suffix} · score {item.get('trust_score')} · {reasons}")

    if cities:
        lines.extend(["", "ГОРОДА"])
        for city in cities[:8]:
            decisions = city.get("decisions") or {}
            lines.append(
                f"{city.get('name') or city.get('slug')}: решений {city.get('total', 0)} · мест {city.get('unique_places', 0)} · "
                f"auto {decisions.get('auto_publish', 0)} · shadow {decisions.get('shadow_auto_publish', 0)} · "
                f"review {decisions.get('send_to_review', 0)} · скрыто {decisions.get(HIDE_DECISION, 0)}"
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
