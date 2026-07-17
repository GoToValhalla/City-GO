from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from models.place import Place
from schemas.user_route import UserRouteBuildRequest, UserRouteState
from services.public_route_place_access import (
    apply_public_route_city_scope,
    load_public_route_place,
    resolve_intent_city_id,
)
from services.route_diversity_policy import normalize_category
from services.user_route_recalc_service import UserRouteRecalcService

RELATED_SLOT_CATEGORIES: dict[str, tuple[str, ...]] = {
    "cafe": ("cafe", "coffee"),
    "food": ("restaurant", "food", "cafe"),
    "restaurant": ("restaurant", "food"),
    "bar": ("bar", "pub"),
    "museum": ("museum", "culture", "gallery"),
    "culture": ("culture", "museum", "gallery", "theatre", "theater"),
    "park": ("park", "walk", "outdoor"),
    "walk": ("walk", "promenade", "park", "landmark"),
    "viewpoint": ("viewpoint", "landmark"),
    "landmark": ("landmark", "attraction", "sight", "monument", "history", "historic"),
    "history": ("history", "historic", "landmark", "museum"),
}


@dataclass(frozen=True)
class SlotMatch:
    slot_id: str
    requested_category: str
    selected_place_id: str | None
    status: str
    explanation: str


class UserRouteSlotBuildService:
    def build(self, db: Session, request: UserRouteBuildRequest) -> UserRouteState:
        places: list[Place] = []
        matches: list[SlotMatch] = []
        used_ids: set[int] = set()
        city_id = resolve_intent_city_id(db, request)

        for index, slot in enumerate(request.route_slots, 1):
            slot_id = str(slot.get("slot_id") or f"slot-{index}")
            requested = normalize_category(slot.get("category") or slot.get("type"))
            required = bool(slot.get("required", True))
            selected_id = _optional_int(slot.get("selected_place_id"))
            place = self._selected_place(db, selected_id, requested, used_ids, city_id=city_id) if selected_id else None
            if place is None:
                place = self._first_slot_candidate(db, request, requested, used_ids, city_id=city_id)
            if place is None:
                status = "missing_required" if required else "missing_optional"
                matches.append(SlotMatch(slot_id, requested, None, status, f"Не нашли подходящую точку для слота {requested or slot_id}."))
                continue
            used_ids.add(int(place.id))
            places.append(place)
            matches.append(SlotMatch(slot_id, requested, str(place.id), "filled", _slot_explanation(requested, place)))

        warnings = [match.explanation for match in matches if match.status.startswith("missing")]
        if not places:
            return UserRouteRecalcService().recalc(
                places=[],
                intent=request,
                revision=1,
                extra_warnings=warnings or ["Не удалось заполнить слоты маршрута."],
            ).model_copy(
                update={
                    "status": "no_route",
                    "partial_reason": "slot_constructor_no_matches",
                    "explanation": {"slot_matches": [match.__dict__ for match in matches]},
                }
            )

        state = UserRouteRecalcService().recalc(
            places=places,
            intent=request,
            revision=1,
            extra_warnings=warnings,
        )
        is_partial = any(match.status == "missing_required" for match in matches)
        explanation = dict(state.explanation or {})
        explanation["slot_matches"] = [match.__dict__ for match in matches]
        explanation["summary"] = "Маршрут собран по заданным слотам." if not is_partial else "Маршрут собран частично: часть слотов не удалось заполнить."
        return state.model_copy(
            update={
                "status": "partial_route" if is_partial else "ready",
                "partial_reason": "slot_constructor_missing_required_slot" if is_partial else None,
                "explanation": explanation,
                "warnings": [*state.warnings, *warnings],
                "has_warnings": bool(state.has_warnings or warnings),
                "warning_count": int(state.warning_count) + len(warnings),
            }
        )

    def _selected_place(
        self,
        db: Session,
        place_id: int | None,
        requested: str,
        used_ids: set[int],
        *,
        city_id: int | None = None,
    ) -> Place | None:
        if not place_id or place_id in used_ids:
            return None
        place = load_public_route_place(db, str(place_id), city_id=city_id)
        if place is None:
            return None
        if requested and not _category_matches(requested, getattr(place, "category", None)):
            return None
        return place

    def _first_slot_candidate(
        self,
        db: Session,
        request: UserRouteBuildRequest,
        requested: str,
        used_ids: set[int],
        *,
        city_id: int | None = None,
    ) -> Place | None:
        if city_id is None:
            city_id = resolve_intent_city_id(db, request)
        categories = RELATED_SLOT_CATEGORIES.get(requested, (requested,)) if requested else ()
        if not categories:
            return None
        query = apply_public_route_city_scope(
            db.query(Place).filter(Place.category.in_(categories)),
            city_id=city_id,
        )
        if used_ids:
            query = query.filter(~Place.id.in_(sorted(used_ids)))
        return query.order_by(Place.id.asc()).first()


def _slot_explanation(requested: str, place: Place) -> str:
    category = normalize_category(getattr(place, "category", None))
    title = getattr(place, "title", None) or "точка"
    if requested == category:
        return f"{title} попала в слот {requested}: категория совпала."
    return f"{title} попала в слот {requested}: использована близкая категория {category}."


def _category_matches(requested: str, category: object) -> bool:
    normalized = normalize_category(category)
    return normalized == requested or category in RELATED_SLOT_CATEGORIES.get(requested, ()) or normalized in RELATED_SLOT_CATEGORIES.get(requested, ())


def _optional_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None
