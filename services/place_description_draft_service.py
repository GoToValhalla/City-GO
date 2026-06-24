"""Create factual, reviewable description drafts for places missing sourced text."""

from __future__ import annotations

import re

from core.place_category_hierarchy import CATEGORY_LABELS_RU
from models.place import Place

TECHNICAL_TITLE = re.compile(r"(?:^|\s)osm[\s:_-]*\d+\s*$|^(?:node|way|relation)[\s:_-]*\d+$", re.I)
CATEGORY_PURPOSE: dict[str, str] = {
    "coffee": "Подойдёт для кофе, короткой остановки или встречи во время прогулки.",
    "food": "Подойдёт для обеда, ужина или остановки на маршруте по городу.",
    "bar": "Подойдёт для вечернего отдыха и встречи с друзьями.",
    "museum": "Подойдёт для знакомства с культурой и историей города.",
    "attraction": "Точку можно включить в обзорную прогулку и использовать как ориентир маршрута.",
    "walk": "Подойдёт для самостоятельной прогулки и спокойного знакомства с окрестностями.",
    "park": "Подойдёт для прогулки, отдыха на свежем воздухе и семейного маршрута.",
    "beach": "Подойдёт для прогулки у воды и сезонного отдыха.",
    "shopping_mall": "Торговая инфраструктура города; в туристический маршрут включается только по практическому сценарию.",
    "pharmacy": "Практическая точка городской инфраструктуры; в прогулочные маршруты по умолчанию не включается.",
    "bank": "Финансовая инфраструктура города; в прогулочные маршруты по умолчанию не включается.",
    "atm": "Практическая точка для снятия наличных; в прогулочные маршруты по умолчанию не включается.",
    "clinic": "Медицинская инфраструктура; перед посещением следует уточнить профиль и часы работы.",
    "hospital": "Медицинское учреждение; в обычные туристические маршруты не включается.",
    "police": "Государственная служба безопасности; в обычные туристические маршруты не включается.",
}


def build_place_description_draft(place: Place) -> str | None:
    """Build a draft only from fields already present on the place.

    The text is intentionally queued for review and never presented as a verified
    editorial description until the normal verification workflow accepts it.
    """
    title = (place.title or "").strip()
    if not title or TECHNICAL_TITLE.search(title):
        return None

    category = (place.canonical_category or place.category or "").strip().lower()
    category_label = CATEGORY_LABELS_RU.get(category, "Место")
    city_name = (getattr(getattr(place, "city", None), "name", None) or "").strip()
    address = (place.address or "").strip()

    location = f" в городе {city_name}" if city_name else ""
    first = f"{title} — {category_label.lower()}{location}."
    facts: list[str] = []
    if address:
        facts.append(f"Находится по адресу: {address}.")
    if place.outdoor and not place.indoor:
        facts.append("Основная часть посещения проходит на открытом воздухе.")
    elif place.indoor and not place.outdoor:
        facts.append("Посещение проходит в помещении.")
    if place.family_friendly:
        facts.append("Место отмечено как подходящее для семейного посещения.")
    if place.dog_friendly:
        facts.append("В карточке указана возможность посещения с собакой.")
    purpose = CATEGORY_PURPOSE.get(category)
    if purpose:
        facts.append(purpose)

    description = " ".join([first, *facts]).strip()
    return description if len(description) >= 80 else None
