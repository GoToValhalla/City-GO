"""Оценка proposed_address для address recovery."""

from __future__ import annotations

import re

from services.place_address_city_only import is_city_only as _is_city_only
from services.place_address_policy import is_generic_address, is_real_address, normalized_address

VENUE_STRICT = frozenset({"cafe", "coffee", "food", "restaurant", "museum", "gallery"})
LOCATION_RELAXED = frozenset({"culture", "walk", "park", "beach", "outdoor", "viewpoint"})
_STREET_HINT = re.compile(
    r"(ул\.|улица|проспект|пр\.|пер\.|переулок|наб\.|набережная|шоссе|бульвар|тракт|"
    r"б-р|пл\.|площадь|lane|road|street|\d)",
    re.IGNORECASE,
)
_HOUSE_HINT = re.compile(r"\d")


def assess_proposed_address(
    address: str | None,
    category: str | None,
    *,
    city_name: str | None = None,
    city_slug: str | None = None,
) -> dict[str, object]:
    proposed = normalized_address(address)
    cat = str(category or "").casefold()
    if not proposed or not is_real_address(proposed):
        return _row(False, "none", "empty_or_placeholder", "Пустой или плейсхолдерный адрес")
    if _is_city_only(proposed, city_name=city_name, city_slug=city_slug):
        return _row(False, "none", "city_only", "Только город без улицы")
    if is_generic_address(proposed, category):
        return _row(False, "low", "generic", "Слишком общий адрес")
    has_street = bool(_STREET_HINT.search(proposed))
    has_house = bool(_HOUSE_HINT.search(proposed))
    if cat in VENUE_STRICT:
        if not has_street:
            return _row(False, "low", "no_street", "Для заведения нужна улица")
        conf = "medium" if has_house else "medium-low"
        return _row(True, conf, "", "Улица" + (" и дом" if has_house else " без дома"))
    if cat in LOCATION_RELAXED or not cat:
        if not has_street:
            return _row(False, "low", "no_street", "Нет уличного компонента")
        conf = "medium" if has_house else "medium-low"
        return _row(True, conf, "", "Локация: улица" + (" и дом" if has_house else " + город"))
    if not has_street:
        return _row(False, "low", "no_street", "Нет уличного компонента")
    return _row(True, "medium" if has_house else "medium-low", "", "Стандартный адрес")


def _row(should_apply: bool, confidence: str, skip_reason: str, comment: str) -> dict[str, object]:
    return {
        "should_apply": should_apply,
        "confidence": confidence,
        "skip_reason": skip_reason,
        "comment": comment,
    }
