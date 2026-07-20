from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from services.route_diversity_policy import is_route_junk_category, normalize_category

WEAK_DESCRIPTION_MIN_LENGTH = 40
LOW_CONFIDENCE_THRESHOLD = 0.35
SAFE_DESCRIPTION_CATEGORIES = {
    "museum": "Культурная точка для прогулки: проверьте актуальные часы работы и детали перед публикацией.",
    "culture": "Культурное место для городского маршрута: описание создано как проверяемый черновик.",
    "park": "Зелёная прогулочная точка: подходит для спокойного маршрута и требует финальной проверки данных.",
    "walk": "Прогулочная точка маршрута: описание создано автоматически и требует проверки редактором.",
    "viewpoint": "Видовая точка для прогулки: проверьте доступность, адрес и актуальность перед публикацией.",
    "landmark": "Городская достопримечательность для маршрута: описание создано автоматически и требует проверки.",
    "history": "Историческая точка маршрута: описание создано как черновик на основе категории и требует проверки.",
}


@dataclass(frozen=True)
class PlaceAutoRepairItem:
    place_id: str
    action: str
    reason: str
    safe: bool
    category: str = "unknown"
    route_eligible: bool | None = None
    route_exclusion_reason: str | None = None
    verification_status: str | None = None


@dataclass(frozen=True)
class PlaceAutoRepairSummary:
    repaired_count: int
    needs_review_count: int
    skipped_count: int
    by_reason: dict[str, int] = field(default_factory=dict)
    by_category: dict[str, int] = field(default_factory=dict)
    items: list[PlaceAutoRepairItem] = field(default_factory=list)


class PlaceAutoRepairService:
    """Deterministic post-import place repair loop.

    The service mutates only fields that are safe to repair without external evidence.
    Unsafe data gaps are returned as review backlog items and can be shown in admin/import summaries.
    """

    def repair_places(self, places: Iterable[object]) -> PlaceAutoRepairSummary:
        items: list[PlaceAutoRepairItem] = []
        for place in places:
            items.extend(self.repair_place(place))
        return _summary(items)

    def repair_place(self, place: object) -> list[PlaceAutoRepairItem]:
        items: list[PlaceAutoRepairItem] = []
        category = normalize_category(getattr(place, "canonical_category", None) or getattr(place, "category", None)) or "unknown"
        place_id = str(getattr(place, "id", "") or getattr(place, "place_id", "") or "unknown")

        if category != (getattr(place, "canonical_category", None) or getattr(place, "category", None) or ""):
            _set_ordinary_field(place, "canonical_category", category)
            _set_ordinary_field(place, "category", category)
            items.append(PlaceAutoRepairItem(place_id, "repair", "category_alias_normalized", True, category))

        if is_route_junk_category(category):
            _set_ordinary_field(place, "tourist_eligible", False)
            _set_ordinary_field(place, "route_policy", "not_for_routes")
            items.append(PlaceAutoRepairItem(
                place_id, "repair", "route_ineligible_utility_or_service", True, category,
                route_eligible=False,
                route_exclusion_reason=f"auto_repair_non_tourist_category:{category}",
            ))

        if _missing_or_weak_address(place):
            normalized = _normalize_address(getattr(place, "address", None))
            if normalized:
                _set_ordinary_field(place, "address", normalized)
                items.append(PlaceAutoRepairItem(place_id, "repair", "address_normalized", True, category))
            else:
                items.append(PlaceAutoRepairItem(place_id, "review", "missing_or_weak_address", False, category))

        if not _has_photo(place):
            chosen = _safe_main_photo(place)
            if chosen:
                _set_ordinary_field(place, "image_url", chosen)
                items.append(PlaceAutoRepairItem(place_id, "repair", "main_photo_selected", True, category))
            else:
                items.append(PlaceAutoRepairItem(place_id, "review", "missing_photo", False, category))

        if _weak_description(place):
            draft = SAFE_DESCRIPTION_CATEGORIES.get(category)
            if draft and _enough_evidence_for_description(place):
                _set_ordinary_field(place, "short_description", draft)
                items.append(PlaceAutoRepairItem(
                    place_id, "repair", "draft_description_created", True, category,
                    verification_status="needs_recheck",
                ))
            else:
                items.append(PlaceAutoRepairItem(place_id, "review", "weak_or_missing_description", False, category))

        if not _has_valid_opening_hours(place):
            items.append(PlaceAutoRepairItem(place_id, "review", "missing_or_invalid_opening_hours", False, category))

        if bool(getattr(place, "is_duplicate_suspected", False)):
            items.append(PlaceAutoRepairItem(place_id, "review", "duplicate_candidate", False, category))

        confidence = getattr(place, "confidence", None)
        if isinstance(confidence, (int, float)) and confidence < LOW_CONFIDENCE_THRESHOLD:
            items.append(PlaceAutoRepairItem(place_id, "review", "low_confidence", False, category))

        return items or [PlaceAutoRepairItem(place_id, "skip", "no_repair_needed", True, category)]


def _summary(items: list[PlaceAutoRepairItem]) -> PlaceAutoRepairSummary:
    by_reason: dict[str, int] = {}
    by_category: dict[str, int] = {}
    for item in items:
        by_reason[item.reason] = by_reason.get(item.reason, 0) + 1
        by_category[item.category] = by_category.get(item.category, 0) + 1
    return PlaceAutoRepairSummary(
        repaired_count=sum(1 for item in items if item.action == "repair"),
        needs_review_count=sum(1 for item in items if item.action == "review"),
        skipped_count=sum(1 for item in items if item.action == "skip"),
        by_reason=by_reason,
        by_category=by_category,
        items=items,
    )


def _set_ordinary_field(place: object, field_name: str, value: object) -> None:
    """Assign one of the auto-repair ordinary (non-controlled) fields via a literal target."""
    if field_name == "canonical_category":
        place.canonical_category = value
    elif field_name == "category":
        place.category = value
    elif field_name == "tourist_eligible":
        place.tourist_eligible = value
    elif field_name == "route_policy":
        place.route_policy = value
    elif field_name == "address":
        place.address = value
    elif field_name == "image_url":
        place.image_url = value
    elif field_name == "short_description":
        place.short_description = value


def _missing_or_weak_address(place: object) -> bool:
    return not bool(_normalize_address(getattr(place, "address", None)))


def _normalize_address(value: object) -> str:
    return " ".join(str(value or "").replace("\n", " ").split())


def _has_photo(place: object) -> bool:
    return bool(str(getattr(place, "image_url", "") or "").strip())


def _safe_main_photo(place: object) -> str | None:
    images = list(getattr(place, "images", []) or [])
    for image in images:
        url = str(getattr(image, "url", "") or getattr(image, "image_url", "") or "").strip()
        if not url:
            continue
        is_public = bool(getattr(image, "is_public", True))
        is_rejected = bool(getattr(image, "is_rejected", False))
        if is_public and not is_rejected:
            return url
    return None


def _weak_description(place: object) -> bool:
    description = str(getattr(place, "short_description", "") or "").strip()
    return len(description) < WEAK_DESCRIPTION_MIN_LENGTH


def _enough_evidence_for_description(place: object) -> bool:
    return bool(str(getattr(place, "title", "") or "").strip()) and bool(normalize_category(getattr(place, "category", None)))


def _has_valid_opening_hours(place: object) -> bool:
    value = getattr(place, "opening_hours", None)
    if value is None:
        return False
    if isinstance(value, dict):
        return bool(value)
    if isinstance(value, str):
        return bool(value.strip())
    return False
