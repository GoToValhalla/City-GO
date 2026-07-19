"""Автоматическая нормализация, конфликты и quality issues для одного места."""

from __future__ import annotations

import hashlib
from datetime import datetime

from sqlalchemy.orm import Session

from models.place import Place
from models.source_observation import SourceObservation
from models.taxonomy import QualityIssue, QualityRule, TaxonomyConflict
from services.place_change_review_service import propose_place_change
from services.quality_score_v2 import calculate_quality_v2
from services.route_policy_service import evaluate_category_policy
from services.taxonomy_rule_engine import classify_place, persist_decision

QUALITY_RULES = (
    ("address_required", "Указан адрес", "warning", {}, False, False),
    ("photo_required", "Добавлено фото", "warning", {}, False, False),
    ("description_min_length", "Описание достаточно подробное", "warning", {"min_length": 80}, False, False),
    ("coordinates_valid", "Координаты корректны", "critical", {}, True, True),
    ("category_active", "Категория существует и активна", "critical", {}, True, True),
    ("opening_hours_valid", "Часы работы имеют допустимый формат", "warning", {}, False, False),
    ("contacts_valid", "Телефон и сайт имеют допустимый формат", "warning", {}, False, False),
    ("description_not_technical", "Описание не содержит технический текст", "warning", {}, True, False),
    ("title_not_raw_key", "Название не является техническим ключом", "critical", {}, True, True),
    ("duplicate_risk", "Нет вероятного дубликата", "critical", {}, True, True),
    ("route_policy_match", "Допуск в маршрут соответствует таксономии", "warning", {}, False, True),
)


def ensure_quality_rules(db: Session) -> None:
    existing = {row.code for row in db.query(QualityRule.code).all()}
    for code, name, severity, parameters, block_publication, block_route in QUALITY_RULES:
        if code not in existing:
            db.add(
                QualityRule(
                    code=code,
                    name_ru=name,
                    severity=severity,
                    entity_type="place",
                    active=True,
                    parameters=parameters,
                    auto_fix_available=code in {"route_policy_match"},
                    blocking_publication=block_publication,
                    blocking_route_eligibility=block_route,
                )
            )
    db.flush()


def normalize_place(
    db: Session,
    place: Place,
    *,
    actor: str = "workflow",
    job_id: int | None = None,
) -> dict[str, object]:
    """Mutate taxonomy only; the enclosing workflow owns derived-state reconciliation."""
    observation = (
        db.query(SourceObservation)
        .filter(SourceObservation.canonical_place_id == place.id)
        .order_by(SourceObservation.last_seen_at.desc())
        .first()
    )
    tags = _source_tags(observation)
    result = classify_place(
        db,
        source=observation.source_type if observation else place.source,
        source_tags=tags,
        title=place.title,
        description=place.short_description,
        current_category=place.category,
    )
    applied = False
    if result.decision == "auto_apply" and result.category_id:
        category = (
            db.query(type(place.category_ref)).filter_by(id=result.category_id).first()
            if place.category_ref is not None
            else None
        )
        if category is None:
            from models.category import Category

            category = db.query(Category).filter(Category.id == result.category_id).first()
        if category:
            proposed = {
                "category_id": category.id,
                "category": category.code,
                "canonical_category": category.code,
            }
            if propose_place_change(
                db,
                place=place,
                proposed=proposed,
                reason="taxonomy_auto_normalization",
                job_id=job_id,
            ):
                old = place.category_id
                place.category_id = category.id
                place.category = category.code
                place.canonical_category = category.code
                persist_decision(db, place_id=place.id, result=result, actor=actor, old_category_id=old)
                applied = True
    if not applied:
        _upsert_conflict(db, place, result, source=observation.source_type if observation else place.source)
    return {**result.to_dict(), "applied": applied}


def validate_place(db: Session, place: Place) -> dict[str, object]:
    ensure_quality_rules(db)
    quality = calculate_quality_v2(place)
    place.quality_score = quality.score
    place.quality_tier = quality.bucket
    failures = _failures(place)
    rules = db.query(QualityRule).filter(QualityRule.active.is_(True), QualityRule.entity_type == "place").all()
    rule_code_by_id = {int(rule.id): rule.code for rule in rules}
    open_codes: set[str] = set()

    for rule in rules:
        details = failures.get(rule.code)
        if details is None:
            continue
        open_codes.add(rule.code)
        fingerprint = hashlib.sha256(f"{place.id}:{rule.code}:{details}".encode()).hexdigest()[:32]
        issue = (
            db.query(QualityIssue)
            .filter(
                QualityIssue.rule_id == rule.id,
                QualityIssue.place_id == place.id,
                QualityIssue.status == "open",
            )
            .first()
        )
        if issue is None:
            issue = QualityIssue(
                rule_id=rule.id,
                place_id=place.id,
                fingerprint=fingerprint,
                severity=rule.severity,
                status="open",
                details={"message": details},
            )
        else:
            issue.fingerprint = fingerprint
            issue.details = {"message": details}
            issue.updated_at = datetime.utcnow()
        db.add(issue)

    open_issues = db.query(QualityIssue).filter(
        QualityIssue.place_id == place.id,
        QualityIssue.status == "open",
    ).all()
    for issue in open_issues:
        rule_code = rule_code_by_id.get(int(issue.rule_id))
        if rule_code is not None and rule_code not in open_codes:
            issue.status = "fixed"
            issue.fixed_at = datetime.utcnow()
            db.add(issue)

    db.add(place)
    return quality.to_dict()


def _upsert_conflict(db: Session, place: Place, result: object, *, source: str | None) -> TaxonomyConflict:
    conflict_type = "no_mapping" if result.category_id is None else "ambiguous_rule" if result.alternatives else "source_mismatch"
    if place.category_id is None:
        conflict_type = "missing_category"
    elif place.category_ref and not place.category_ref.is_active:
        conflict_type = "archived_category"
    elif (place.category or "").lower() in {"service", "services", "unknown"}:
        conflict_type = "raw_backend_key"
    existing = (
        db.query(TaxonomyConflict)
        .filter(
            TaxonomyConflict.place_id == place.id,
            TaxonomyConflict.conflict_type == conflict_type,
            TaxonomyConflict.status == "open",
        )
        .first()
    )
    if existing is None:
        existing = TaxonomyConflict(
            place_id=place.id,
            conflict_type=conflict_type,
            severity="critical" if conflict_type in {"missing_category", "archived_category"} else "warning",
            source=source,
            confidence=result.confidence,
            current_category_id=place.category_id,
            recommended_category_id=result.category_id,
            details={
                "explanation": result.explanation,
                "warnings": result.warnings,
                "alternatives": result.alternatives,
            },
            status="open",
        )
    else:
        existing.confidence = result.confidence
        existing.recommended_category_id = result.category_id
        existing.details = {
            "explanation": result.explanation,
            "warnings": result.warnings,
            "alternatives": result.alternatives,
        }
    db.add(existing)
    return existing


def _source_tags(observation: SourceObservation | None) -> dict[str, object]:
    if observation is None:
        return {}
    payload = observation.raw_payload or {}
    tags = payload.get("tags") if isinstance(payload, dict) else None
    if isinstance(tags, dict):
        return tags
    return {"legacy_category": observation.raw_category} if observation.raw_category else {}


def _failures(place: Place) -> dict[str, str]:
    failures: dict[str, str] = {}
    if not (place.address or "").strip():
        failures["address_required"] = "Не указан адрес."
    if not place.image_url and not place.images:
        failures["photo_required"] = "Нет подтверждённого фото."
    if len((place.short_description or "").strip()) < 80:
        failures["description_min_length"] = "Описание короче 80 символов."
    if place.lat is None or place.lng is None or (place.lat == 0 and place.lng == 0):
        failures["coordinates_valid"] = "Координаты отсутствуют или равны 0,0."
    if place.category_ref is None or not place.category_ref.is_active:
        failures["category_active"] = "Категория отсутствует или архивирована."
    if place.opening_hours is not None and not isinstance(place.opening_hours, dict):
        failures["opening_hours_valid"] = "Часы работы имеют неверный формат."
    technical = (place.short_description or "").lower()
    if any(token in technical for token in ("amenity=", "tourism=", "shop=", "osm_id")):
        failures["description_not_technical"] = "Описание содержит технические поля источника."
    title = (place.title or "").lower()
    if any(token in title for token in ("amenity=", "tourism=", "shop=", "node/")):
        failures["title_not_raw_key"] = "Название похоже на raw key."
    if place.is_duplicate_suspected:
        failures["duplicate_risk"] = "Есть риск дубликата."
    if place.category_ref and place.is_route_eligible != evaluate_category_policy(
        place.category_ref,
        context="tourist_walk",
    ).allowed:
        failures["route_policy_match"] = "Флаг маршрута расходится с политикой категории."
    return failures
