"""Re-export каталога feature toggles (обратная совместимость)."""

from services.feature_toggle_catalog import (
    CITY_TOGGLE_KEYS,
    CITY_TOGGLES,
    GLOBAL_TOGGLES,
    GROUP_LABELS,
    TOGGLE_GROUPS,
)
from services.feature_toggle_catalog.types import ToggleDef

__all__ = (
    "ToggleDef",
    "GLOBAL_TOGGLES",
    "CITY_TOGGLES",
    "CITY_TOGGLE_KEYS",
    "TOGGLE_GROUPS",
    "GROUP_LABELS",
)
