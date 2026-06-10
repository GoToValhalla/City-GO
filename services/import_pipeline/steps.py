"""Шаги pipeline импорта/обогащения города."""

from __future__ import annotations

STEP_CREATED = "created"
STEP_QUEUED = "queued"
STEP_RUNNING = "running"
STEP_COLLECTING_PLACES = "collecting_places"
STEP_FINDING_ADDRESSES = "finding_addresses"
STEP_FINDING_IMAGES = "finding_images"
STEP_PREPARING_DESCRIPTIONS = "preparing_descriptions"
STEP_CATEGORIES_TAGS = "categories_tags"
STEP_COMPUTING_QUALITY = "computing_quality"
STEP_COMPUTING_READINESS = "computing_readiness"
STEP_READY_FOR_REVIEW = "ready_for_review"
STEP_ERROR = "error"
STEP_CANCELLED = "cancelled"

STALL_THRESHOLD_MINUTES = 30

STEP_LABELS: dict[str, str] = {
    STEP_CREATED: "Создано",
    STEP_QUEUED: "В очереди",
    STEP_RUNNING: "Выполняется",
    STEP_COLLECTING_PLACES: "Собираем места",
    STEP_FINDING_ADDRESSES: "Ищем адреса",
    STEP_FINDING_IMAGES: "Ищем фотографии",
    STEP_PREPARING_DESCRIPTIONS: "Требует ручной обработки",
    STEP_CATEGORIES_TAGS: "Проверяем категории",
    STEP_COMPUTING_QUALITY: "Считаем качество",
    STEP_COMPUTING_READINESS: "Готовность маршрутов",
    STEP_READY_FOR_REVIEW: "Готово к проверке",
    STEP_ERROR: "Ошибка",
    STEP_CANCELLED: "Отменено",
}

TERMINAL_STEPS = frozenset({STEP_READY_FOR_REVIEW, STEP_ERROR, STEP_CANCELLED})
