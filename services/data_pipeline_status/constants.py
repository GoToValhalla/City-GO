"""Канонические очереди и русские подписи Data Pipeline."""

from __future__ import annotations

CANONICAL_QUEUE_CODES = ("import", "enrichment", "photo_review", "verification")

QUEUE_LABELS: dict[str, str] = {
    "import": "Импорт данных",
    "enrichment": "Обогащение",
    "photo_review": "Проверка фотографий",
    "verification": "Проверка мест",
}

RUN_TYPE_LABELS: dict[str, str] = {
    "admin_city_import": "Импорт города",
    "enrichment_only": "Обогащение",
    "photo_enrichment": "Обогащение фото",
    "address_enrichment": "Обогащение адресов",
    "snapshot_refresh": "Обновление снимка",
    "city_enrichment": "Обогащение города",
    "pipeline": "Конвейер данных",
}

RUN_STATUS_LABELS: dict[str, str] = {
    "queued": "В очереди",
    "running": "Выполняется",
    "completed": "Завершён",
    "failed": "Ошибка",
    "stalled": "Завис",
    "cancelled": "Отменён",
}

SECTION_LABELS: dict[str, str] = {
    "imports": "Импорт",
    "enrichment": "Обогащение",
    "photos": "Фотографии",
    "verification": "Проверка мест",
    "coordinates": "Координаты",
}
