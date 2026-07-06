"""Deterministic ranking and tiering for discovery candidates."""

from __future__ import annotations

from schemas.destination_discovery import ConfidenceScore, DiscoveryTier

_TYPE_WEIGHT = {"city": 1.0, "town": 0.75, "village": 0.45, "resort": 0.8, "area": 0.55}


def score_candidate(raw: dict[str, object], *, existing_boost: float = 0.0) -> tuple[float, ConfidenceScore, DiscoveryTier, list[str]]:
    dest_type = str(raw.get("type") or "unknown")
    population = int(raw.get("population") or 0)
    importance = float(raw.get("importance") or 0.5)
    has_bbox = raw.get("bbox") is not None
    type_weight = _TYPE_WEIGHT.get(dest_type, 0.4)
    pop_signal = min(population / 500_000, 1.0) if population else None
    data_availability = 0.85 if has_bbox else 0.35
    tourist = min(0.35 + importance * 0.45 + type_weight * 0.2, 1.0)
    name_consistency = 0.9 if raw.get("english_name") else 0.6
    poi_signal = None if raw.get("poi_unknown") else None
    wiki_signal = None
    overall_parts = [tourist * 0.35, data_availability * 0.25, type_weight * 0.2, importance * 0.2]
    if pop_signal is not None:
        overall_parts.append(pop_signal * 0.1)
    overall = min(sum(overall_parts) + existing_boost, 1.0)
    reasons = [f"Тип: {dest_type}", f"Важность источника: {importance:.2f}"]
    if population:
        reasons.append(f"Население: {population}")
    if has_bbox:
        reasons.append("Границы bbox доступны")
    else:
        reasons.append("Границы bbox отсутствуют")
    if existing_boost:
        reasons.append("Найдено совпадение с существующим направлением")
    if raw.get("poi_unknown"):
        reasons.append("POI-сигнал недоступен")
    confidence = ConfidenceScore(
        overall=round(overall, 3),
        tourist_potential=round(tourist, 3),
        data_availability=round(data_availability, 3),
        name_consistency=round(name_consistency, 3),
        existing_signal=round(existing_boost, 3) if existing_boost else None,
        poi_signal=poi_signal,
        wiki_signal=wiki_signal,
        reasons=reasons,
    )
    tier = _tier_for(overall, dest_type)
    ranking = round(overall * 100 + importance * 10 + (population / 10000 if population else 0), 3)
    return ranking, confidence, tier, reasons


def _tier_for(overall: float, dest_type: str) -> DiscoveryTier:
    if dest_type == "city" and overall >= 0.8:
        return "top"
    if overall >= 0.72:
        return "high"
    if overall >= 0.55:
        return "medium"
    if overall >= 0.35:
        return "low"
    return "unknown"
