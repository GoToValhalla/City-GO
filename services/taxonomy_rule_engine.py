"""Объяснимый движок классификации City GO."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from core.place_category_hierarchy import LEGACY_TO_CANONICAL
from models.category import Category
from models.taxonomy import TaxonomyDecision, TaxonomyMapping

HIGH_CONFIDENCE = 0.85
MEDIUM_CONFIDENCE = 0.60


@dataclass(slots=True)
class ClassificationResult:
    category_id: int | None
    category_code: str | None
    confidence: float
    matched_rule_id: int | None
    explanation: str
    decision: str
    warnings: list[str] = field(default_factory=list)
    alternatives: list[dict[str, Any]] = field(default_factory=list)
    def to_dict(self) -> dict[str, Any]: return asdict(self)


def classify_place(db: Session, *, source: str | None, source_tags: dict[str, Any] | None, title: str | None,
    description: str | None, current_category: str | None, manual_category_id: int | None = None,
    city_context: dict[str, Any] | None = None) -> ClassificationResult:
    del city_context
    tags = {str(key).lower(): str(value).lower() for key, value in (source_tags or {}).items() if value is not None}
    tags["__title__"] = title or ""; tags["__description__"] = description or ""
    if manual_category_id is not None:
        category = db.query(Category).filter(Category.id == manual_category_id, Category.is_active.is_(True)).first()
        if category: return ClassificationResult(category.id, category.code, 1.0, None, "Категория выбрана администратором.", "manual")
    candidates = _mapping_candidates(db, source=source, tags=tags)
    if candidates:
        best_score, best = candidates[0]
        alternatives = [{"category_id": mapping.target_category_id, "confidence": round(score, 3), "mapping_id": mapping.id} for score, mapping in candidates[1:4]]
        ambiguous = bool(alternatives and abs(best_score - float(alternatives[0]["confidence"])) < 0.05)
        category = db.query(Category).filter(Category.id == best.target_category_id).first(); warnings = ["Несколько правил дали близкий результат."] if ambiguous else []
        confidence = min(1.0, best_score)
        return ClassificationResult(best.target_category_id, category.code if category else None, confidence, best.id,
            f"Совпало правило {best.source}:{best.source_key}={best.source_value}.", _decision(confidence, ambiguous=ambiguous), warnings, alternatives)
    legacy = (current_category or "").strip().lower(); canonical = LEGACY_TO_CANONICAL.get(legacy)
    if canonical:
        category = db.query(Category).filter(Category.code == canonical, Category.is_active.is_(True)).first()
        if category: return ClassificationResult(category.id, category.code, 0.75, None, f"Применено legacy-сопоставление {legacy} → {canonical}.", "review")
    heuristic = _heuristic_category(db, title=title, description=description)
    if heuristic: return ClassificationResult(heuristic.id, heuristic.code, 0.55, None, "Категория предложена по названию или описанию.", "review", ["Требуется ручная проверка."])
    return ClassificationResult(None, None, 0.0, None, "Подходящее правило не найдено.", "unknown", ["Место добавлено в очередь конфликтов."])


def persist_decision(db: Session, *, place_id: int, result: ClassificationResult, actor: str, old_category_id: int | None, batch_id: str | None = None) -> TaxonomyDecision:
    decision = TaxonomyDecision(place_id=place_id, category_id=result.category_id, mapping_id=result.matched_rule_id,
        decision_type=result.decision, confidence=result.confidence, explanation=result.explanation, warnings=result.warnings,
        alternatives=result.alternatives, old_category_id=old_category_id, actor=actor, batch_id=batch_id)
    db.add(decision); return decision


def _mapping_candidates(db: Session, *, source: str | None, tags: dict[str, str]) -> list[tuple[float, TaxonomyMapping]]:
    query = db.query(TaxonomyMapping).filter(TaxonomyMapping.active.is_(True))
    if source: query = query.filter(TaxonomyMapping.source.in_([source, "any", "text_alias"]))
    candidates: list[tuple[float, TaxonomyMapping]] = []
    for mapping in query.order_by(TaxonomyMapping.priority.desc()).all():
        if not _mapping_matches(mapping, tags): continue
        conditions = mapping.conditions or {}
        if any(tags.get(str(key).lower()) != str(value).lower() for key, value in conditions.items()): continue
        specificity = min(0.08, len(conditions) * 0.02)
        candidates.append((min(1.0, mapping.confidence + specificity + min(mapping.priority, 1000) / 100000), mapping))
    return sorted(candidates, key=lambda item: (item[0], item[1].priority), reverse=True)


def _mapping_matches(mapping: TaxonomyMapping, tags: dict[str, str]) -> bool:
    if mapping.source == "text_alias": return mapping.source_value.lower() in f"{tags.get('__title__', '')} {tags.get('__description__', '')}".lower()
    return tags.get(mapping.source_key.lower()) == mapping.source_value.lower()


def _heuristic_category(db: Session, *, title: str | None, description: str | None) -> Category | None:
    text = f"{title or ''} {description or ''}".lower(); aliases = {"pharmacy": ("аптек", "pharmacy"), "shopping_mall": ("торговый центр", "трц", "mall"), "bank": ("банк",), "atm": ("банкомат", "atm"), "museum": ("музей", "museum"), "park": ("парк",), "coffee": ("кофейн", "coffee"), "hospital": ("больниц", "hospital")}
    for code, needles in aliases.items():
        if any(needle in text for needle in needles): return db.query(Category).filter(Category.code == code, Category.is_active.is_(True)).first()
    return None


def _decision(confidence: float, *, ambiguous: bool) -> str:
    if confidence >= HIGH_CONFIDENCE and not ambiguous: return "auto_apply"
    if confidence >= MEDIUM_CONFIDENCE: return "review"
    return "unknown"
