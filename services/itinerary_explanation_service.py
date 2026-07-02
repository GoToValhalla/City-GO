"""LEGACY ITINERARY EXPLANATION SERVICE.

Status: part of the old `/routes/generate` itinerary stack.

Active explanation source of truth:
- `services.route_explanation_reasons`
- `services.explainability_service`
- `services.route_builder_flow`

Rules:
- Do not add new route explanation product behavior here.
- Keep only for old itinerary endpoint compatibility until consumers migrate.
"""

from models.place import Place


# Маппинг reason-кодов → человекочитаемый текст.
REASON_LABELS = {
    "close_to_start": "рядом со стартом",
    "matches_interest": "соответствует вашему запросу",
    "fits_context": "подходит под текущие ограничения маршрута",
    "local_spot": "выглядит как более локальная точка",
}


# Собирает человекочитаемую причину для конкретной точки.
# Если reasons нет — возвращаем безопасный fallback.
def build_place_reason(place: Place, ranked_reasons: list[str]) -> str:
    if not ranked_reasons:
        return "Рекомендовано как подходящая точка маршрута"

    readable_reasons: list[str] = []

    for reason in ranked_reasons:
        label = REASON_LABELS.get(reason)
        if label:
            readable_reasons.append(label)

    if not readable_reasons:
        return "Подобрано системой как подходящее место"

    return ", ".join(readable_reasons)


# Собирает explanation всего маршрута.
# Объяснение должно быть простым, но полезным:
# - что учитывали
# - сколько точек
# - время
# - дистанцию
# - сценарные ограничения
def build_route_explanation(
    merged_context: dict,
    ordered_places: list[Place],
    estimated_duration_minutes: int | None,
    estimated_distance_km: float | None,
    start_context,
    requested_duration_minutes: int | None,
    duration_fit_score: float | None,
) -> str:
    parts: list[str] = []

    # Базовое описание логики маршрута.
    parts.append("Маршрут собран на основе ваших предпочтений и доступных мест.")

    # Интересы пользователя.
    interests = merged_context.get("preferences", {}).get("interests", [])
    if interests:
        parts.append(f"Учтены интересы: {', '.join(interests)}.")

    # Anti-tourist сценарий.
    if merged_context.get("preferences", {}).get("anti_tourist"):
        parts.append("Сделан акцент на менее туристических и более локальных местах.")

    # Контекстные ограничения.
    if merged_context.get("with_dog"):
        parts.append("Маршрут адаптирован под прогулку с собакой.")

    if merged_context.get("with_children"):
        parts.append("Маршрут учитывает сценарий с детьми.")

    if merged_context.get("indoor_only"):
        parts.append("В приоритете крытые точки.")

    if merged_context.get("outdoor_only"):
        parts.append("В приоритете уличные точки.")

    # Режим передвижения.
    route_mode = merged_context.get("route_mode")
    if route_mode:
        parts.append(f"Режим маршрута: {route_mode}.")

    # Временные ограничения.
    if requested_duration_minutes is not None:
        parts.append(
            f"Целевой лимит времени — около {requested_duration_minutes} минут."
        )

    if estimated_duration_minutes is not None:
        parts.append(
            f"Оценочное время маршрута — около {estimated_duration_minutes} минут."
        )

    if duration_fit_score is not None:
        parts.append(f"Соответствие целевому времени: {int(duration_fit_score * 100)}%.")

    # Дистанция маршрута.
    if estimated_distance_km is not None:
        parts.append(f"Оценочная дистанция маршрута — около {estimated_distance_km:.1f} км.")

    # Количество точек.
    parts.append(f"Всего точек в маршруте: {len(ordered_places)}.")

    return " ".join(parts)
