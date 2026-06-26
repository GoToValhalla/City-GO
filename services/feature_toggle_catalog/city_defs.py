from services.feature_toggle_catalog.types import ToggleDef

CITY_TOGGLES: tuple[ToggleDef, ...] = (
    {"key": "city_visible_to_users", "label": "Город опубликован", "description": "Включает или снимает город с публикации для сайта и Telegram", "default": False, "scope": "city", "group": "visibility"},
    {"key": "admin_only_city", "label": "Только для админов", "description": "Город скрыт от публики", "default": False, "scope": "city", "group": "visibility"},
    {"key": "test_city", "label": "Тестовый город", "description": "Помечен как тестовый", "default": False, "scope": "city", "group": "visibility"},
    {"key": "web_enabled", "label": "Web для города", "description": "Операционная настройка Web; публичный список городов общий с Telegram", "default": True, "scope": "city", "group": "channels"},
    {"key": "telegram_enabled", "label": "Telegram для города", "description": "Операционная настройка Telegram; публичный список городов общий с сайтом", "default": True, "scope": "city", "group": "channels"},
    {"key": "route_generation_enabled", "label": "Маршруты в городе", "description": "Генерация маршрутов для города", "default": True, "scope": "city", "group": "routes"},
    {"key": "ai_recommendations_enabled", "label": "AI-рекомендации", "description": "Рекомендации для города", "default": True, "scope": "city", "group": "ai"},
    {"key": "import_enabled", "label": "Импорт мест", "description": "Разрешён импорт в город", "default": True, "scope": "city", "group": "data"},
    {"key": "auto_enrichment_enabled", "label": "Автообогащение", "description": "Фоновое обогащение в городе", "default": False, "scope": "city", "group": "data"},
    {"key": "auto_photo_enabled", "label": "Автофото", "description": "Автоподбор фото для мест", "default": False, "scope": "city", "group": "data"},
    {"key": "manual_verification_required", "label": "Ручная верификация", "description": "Места требуют ручной проверки", "default": False, "scope": "city", "group": "quality"},
    {"key": "verified_places_only", "label": "Только verified", "description": "В каталоге только проверенные места", "default": False, "scope": "city", "group": "quality"},
    {"key": "hide_without_photo", "label": "Скрывать без фото", "description": "Не показывать места без фото", "default": False, "scope": "city", "group": "quality"},
    {"key": "hide_without_address", "label": "Скрывать без адреса", "description": "Не показывать места без адреса", "default": False, "scope": "city", "group": "quality"},
    {"key": "hide_low_quality", "label": "Скрывать низкое качество", "description": "Скрывать места с низкой уверенностью", "default": False, "scope": "city", "group": "quality"},
)

CITY_TOGGLE_KEYS: tuple[str, ...] = tuple(item["key"] for item in CITY_TOGGLES)
