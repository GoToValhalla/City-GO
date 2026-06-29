from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from sqlalchemy.orm import Session

from models.city import City
from models.known_missing_poi import KnownMissingPoi
from models.source_observation import SourceObservation
from services.coverage_gap_service import CRITICAL_POLICIES, MATCHED_STATUSES, refresh_coverage_statuses
from services.coverage_scope_suggestion_service import suggest_scopes_for_gaps
from services.data_coverage_contract import (
    BLOCKING_GAP_REASONS,
    MIN_MUST_HAVE_COVERAGE_RATIO,
    UNRESOLVED_STATUSES,
    gap_reason_is_explained,
    scope_aliases,
)
from services.osm_import_taxonomy import category_from_osm_tags, unsupported_tag_reason

ROOT_DIR = Path(__file__).resolve().parents[1]
IMPORT_TARGETS_PATH = ROOT_DIR / "data" / "config" / "import_targets.json"

EXPLANATION_ACTIONS = {
    "outside_bbox": "Расширить bbox или добавить scope для туристического кластера.",
    "not_imported_scope": "Добавить import scope нужного типа или связать expected_scope с legacy scope.",
    "unsupported_tag": "Расширить OSM taxonomy/profile и повторить dry-run import.",
    "source_absent": "Подтвердить отсутствие в источниках или добавить curated POI.",
    "hidden_by_policy": "Проверить статус источника и policy скрытия.",
    "missing_name": "Исправить нормализацию имени или добавить ручной alias.",
    "missing_coordinates": "Исправить координаты source observation.",
    "duplicate_candidate": "Смержить дубли и закрепить canonical place.",
    "not_visible_in_catalog": "Проверить publication/visibility policy найденного места.",
    "not_route_eligible": "Проверить route eligibility, place layer и route policy для must-have места.",
}


def run_data_coverage_assurance(db: Session, *, city_slug: str | None = None) -> dict[str, Any]:
    """Runs full Data Coverage Assurance pass and mutates known_missing_poi statuses."""

    base_result = refresh_coverage_statuses(db, city_slug=city_slug)
    rows = _query_rows(db, city_slug=city_slug)

    changed_by_assurance = 0
    for row in rows:
        previous = (row.status, row.gap_reason)
        _apply_scope_assurance(row)
        _apply_source_observation_assurance(db, row)
        if previous != (row.status, row.gap_reason):
            changed_by_assurance += 1
            row.updated_at = datetime.utcnow()

    db.flush()
    rows = _query_rows(db, city_slug=city_slug)
    suggestions = suggest_scopes_for_gaps(rows)

    return {
        **base_result,
        "changed_by_assurance": changed_by_assurance,
        "summary": build_summary(rows),
        "acceptance": build_acceptance(rows),
        "weekly_check": build_weekly_report(rows),
        "recommended_actions": build_recommended_actions(rows),
        "scope_suggestions": [suggestion.__dict__ for suggestion in suggestions],
    }


def build_summary(rows: Iterable[KnownMissingPoi]) -> dict[str, Any]:
    row_list = list(rows)
    by_status = Counter(row.status for row in row_list)
    by_gap_reason = Counter(row.gap_reason or "none" for row in row_list)
    by_category = Counter(row.expected_category for row in row_list)
    by_scope = Counter(row.expected_scope for row in row_list)
    critical = [row for row in row_list if row.expected_route_policy in CRITICAL_POLICIES]
    matched_critical = [row for row in critical if row.status in MATCHED_STATUSES]
    blocking_critical = [row for row in critical if row.gap_reason in BLOCKING_GAP_REASONS]

    return {
        "total": len(row_list),
        "matched": by_status.get("matched", 0),
        "unresolved": sum(1 for row in row_list if row.status in UNRESOLVED_STATUSES),
        "critical_unresolved": len(critical) - len(matched_critical),
        "blocking_critical": len(blocking_critical),
        "must_have_coverage_ratio": round(len(matched_critical) / len(critical), 4) if critical else 1.0,
        "by_status": dict(by_status),
        "by_gap_reason": dict(by_gap_reason),
        "by_expected_category": dict(by_category),
        "by_expected_scope": dict(by_scope),
    }


def build_acceptance(rows: Iterable[KnownMissingPoi]) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[KnownMissingPoi]] = defaultdict(list)
    for row in rows:
        grouped[row.city.slug if row.city else "unknown"].append(row)
    return {city_slug: _city_acceptance(city_slug, city_rows) for city_slug, city_rows in grouped.items()}


def build_weekly_report(rows: Iterable[KnownMissingPoi]) -> dict[str, object]:
    row_list = list(rows)
    return {
        "checked_at": datetime.utcnow().isoformat(),
        "closed_or_hidden": [_row_id(row) for row in row_list if row.gap_reason == "hidden_by_policy"],
        "not_reconciled": [_row_id(row) for row in row_list if row.status in {"missing", "needs_review"}],
        "scope_expansion_required": [
            _row_id(row) for row in row_list if row.gap_reason in {"outside_bbox", "not_imported_scope"}
        ],
        "taxonomy_expansion_required": [_row_id(row) for row in row_list if row.gap_reason == "unsupported_tag"],
        "route_visibility_required": [
            _row_id(row) for row in row_list if row.gap_reason in {"not_visible_in_catalog", "not_route_eligible"}
        ],
    }


def build_recommended_actions(rows: Iterable[KnownMissingPoi]) -> list[dict[str, object]]:
    counters = Counter(row.gap_reason for row in rows if row.gap_reason)
    return [
        {
            "gap_reason": reason,
            "count": count,
            "action": EXPLANATION_ACTIONS.get(reason or "", "Ручная проверка."),
        }
        for reason, count in counters.most_common()
    ]


def _query_rows(db: Session, *, city_slug: str | None) -> list[KnownMissingPoi]:
    query = db.query(KnownMissingPoi).join(City, City.id == KnownMissingPoi.city_id)
    if city_slug:
        query = query.filter(City.slug == city_slug)
    return query.order_by(City.slug.asc(), KnownMissingPoi.slug.asc()).all()


def _apply_scope_assurance(row: KnownMissingPoi) -> None:
    if row.status in MATCHED_STATUSES:
        return

    scope_status = _scope_status_for_row(row)
    if scope_status == "outside_bbox":
        row.status = "out_of_scope"
        row.gap_reason = "outside_bbox"
        row.review_notes = "Coverage assurance: point is outside every configured city import scope."
    elif scope_status == "not_imported_scope" and row.gap_reason in {None, "source_absent", "outside_bbox"}:
        row.status = "out_of_scope"
        row.gap_reason = "not_imported_scope"
        row.review_notes = (
            "Coverage assurance: point is inside city import area, "
            f"but expected scope '{row.expected_scope}' is not configured."
        )


def _apply_source_observation_assurance(db: Session, row: KnownMissingPoi) -> None:
    if row.status in MATCHED_STATUSES or row.gap_reason in {"outside_bbox", "not_imported_scope"}:
        return
    observation = _nearest_observation(db, row)
    if observation is None:
        return
    tags = _observation_tags(observation)
    taxonomy_reason = unsupported_tag_reason(tags)
    if taxonomy_reason == "unsupported_tag":
        row.status = "tag_unsupported"
        row.gap_reason = "unsupported_tag"
        row.review_notes = f"Coverage assurance: source observation #{observation.id} has meaningful unsupported tags."
        return
    if category_from_osm_tags(tags) and observation.canonical_place_id is None:
        row.status = "needs_review"
        row.gap_reason = "not_imported_scope"
        row.review_notes = (
            f"Coverage assurance: source observation #{observation.id} is supported by taxonomy "
            "but did not become a visible place."
        )


def _city_acceptance(city_slug: str, rows: list[KnownMissingPoi]) -> dict[str, object]:
    critical = [row for row in rows if row.expected_route_policy in CRITICAL_POLICIES]
    matched = [row for row in critical if row.status in MATCHED_STATUSES]
    explained = [row for row in critical if row.status in MATCHED_STATUSES or gap_reason_is_explained(row.gap_reason)]
    blocking = [row for row in critical if row.gap_reason in BLOCKING_GAP_REASONS]
    coverage_ratio = round(len(matched) / len(critical), 4) if critical else 1.0
    reasons: list[str] = []
    if coverage_ratio < MIN_MUST_HAVE_COVERAGE_RATIO:
        reasons.append("must_have_coverage_below_threshold")
    if len(explained) < len(critical):
        reasons.append("must_have_without_explanation")
    if blocking:
        reasons.append("blocking_gap_reasons_present")
    return {
        "city_slug": city_slug,
        "accepted": not reasons,
        "reasons": reasons,
        "total_critical": len(critical),
        "matched_critical": len(matched),
        "explained_critical": len(explained),
        "unresolved_critical": len(critical) - len(matched),
        "blocking_critical": len(blocking),
        "coverage_ratio": coverage_ratio,
        "threshold": MIN_MUST_HAVE_COVERAGE_RATIO,
    }


def _scope_status_for_row(row: KnownMissingPoi) -> str:
    payload = _load_import_targets()
    city_slug = row.city.slug if row.city else None
    city_scopes = [
        scope
        for city in payload.get("targets", [])
        if city.get("city") == city_slug
        for scope in city.get("scopes", [])
        if scope.get("enabled", True)
    ]
    if not city_scopes:
        return "outside_bbox"
    inside_any = False
    inside_expected = False
    expected_aliases = scope_aliases(row.expected_scope)
    for scope in city_scopes:
        if not _bbox_contains(scope.get("bbox") or {}, lat=row.lat, lng=row.lng):
            continue
        inside_any = True
        scope_keys = {str(scope.get("code") or ""), str(scope.get("profile") or ""), str(scope.get("scope_type") or "")}
        if expected_aliases & scope_keys:
            inside_expected = True
    if inside_expected:
        return "inside_expected_scope"
    if inside_any:
        return "not_imported_scope"
    return "outside_bbox"


def _nearest_observation(db: Session, row: KnownMissingPoi) -> SourceObservation | None:
    observations = (
        db.query(SourceObservation)
        .filter(SourceObservation.city_id == row.city_id, SourceObservation.raw_lat.isnot(None), SourceObservation.raw_lng.isnot(None))
        .order_by(SourceObservation.id.desc())
        .limit(1000)
        .all()
    )
    best: tuple[float, SourceObservation] | None = None
    for observation in observations:
        if observation.raw_lat is None or observation.raw_lng is None:
            continue
        distance = _distance_m(row.lat, row.lng, observation.raw_lat, observation.raw_lng)
        if distance > 650:
            continue
        if best is None or distance < best[0]:
            best = (distance, observation)
    return best[1] if best else None


def _load_import_targets() -> dict[str, Any]:
    if not IMPORT_TARGETS_PATH.exists():
        return {"targets": []}
    return json.loads(IMPORT_TARGETS_PATH.read_text(encoding="utf-8"))


def _bbox_contains(bbox: dict[str, Any], *, lat: float, lng: float) -> bool:
    try:
        return float(bbox["south"]) <= lat <= float(bbox["north"]) and float(bbox["west"]) <= lng <= float(bbox["east"])
    except (KeyError, TypeError, ValueError):
        return False


def _observation_tags(observation: SourceObservation) -> dict[str, Any]:
    payload = observation.raw_payload if isinstance(observation.raw_payload, dict) else {}
    tags = payload.get("tags") if isinstance(payload, dict) else {}
    return tags if isinstance(tags, dict) else {}


def _distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius_m = 6_371_000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lng2 - lng1)
    a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    return radius_m * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _row_id(row: KnownMissingPoi) -> dict[str, object]:
    return {
        "id": row.id,
        "city_slug": row.city.slug if row.city else None,
        "slug": row.slug,
        "name": row.name_ru or row.name_en or row.name_local or row.slug,
        "status": row.status,
        "gap_reason": row.gap_reason,
    }
