from services.feature_toggle_catalog.city_defs import CITY_TOGGLE_KEYS, CITY_TOGGLES
from services.feature_toggle_catalog.global_defs import GLOBAL_TOGGLES
from services.feature_toggle_catalog.types import ToggleDef

TOGGLE_GROUPS: tuple[str, ...] = ("product", "routes", "ai", "moderation", "data", "system", "visibility", "channels", "quality")

GROUP_LABELS: dict[str, str] = {
    "product": "Продукт",
    "routes": "Маршруты",
    "ai": "AI",
    "moderation": "Модерация",
    "data": "Данные и импорт",
    "system": "Система",
    "visibility": "Видимость города",
    "channels": "Каналы",
    "quality": "Качество данных",
}
