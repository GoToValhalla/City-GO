from __future__ import annotations

from dataclasses import dataclass

# Единый контракт Data Coverage Assurance.
# Он нужен, чтобы backend, import profiles, readiness gate, admin UI и тесты
# не расходились в статусах/причинах/типах scope.

MATCHED_STATUSES = {"matched"}

UNRESOLVED_STATUSES = {
    "missing",
    "needs_review",
    "source_absent",
    "out_of_scope",
    "tag_unsupported",
    "rejected_policy",
    "duplicate",
}

COVERAGE_STATUSES = MATCHED_STATUSES | UNRESOLVED_STATUSES

CRITICAL_POLICIES = {"must_have", "day_trip"}

GAP_REASONS = {
    "outside_bbox",
    "unsupported_tag",
    "source_absent",
    "hidden_by_policy",
    "missing_name",
    "missing_coordinates",
    "duplicate_candidate",
    "not_imported_scope",
    "not_visible_in_catalog",
    "not_route_eligible",
}

# Причины, которые требуют обязательного продуктового решения до публикации города.
# Они означают, что важное место либо нельзя импортировать текущими правилами,
# либо оно есть, но не попадает в каталог/маршруты.
BLOCKING_GAP_REASONS = {
    "outside_bbox",
    "unsupported_tag",
    "not_imported_scope",
    "not_visible_in_catalog",
    "not_route_eligible",
    "duplicate_candidate",
}

EXPLAINED_GAP_REASONS = GAP_REASONS - {"unsupported_tag"}

SCOPE_TYPES = {
    "urban_core",
    "food_core",
    "heritage_ring",
    "nature_daytrip",
    "regional_attractions",
    "useful_services",
}

# Backward-compatible aliases для старых import_targets.
# Новый seed может требовать urban_core/food_core/heritage_ring, а старые scope-коды
# в конфиге пока называются tourist_core/food_area/heritage_ne_ring.
SCOPE_ALIASES: dict[str, set[str]] = {
    "urban_core": {"urban_core", "tourist_core"},
    "food_core": {"food_core", "food_area", "food_wider_center", "food_and_coffee"},
    "heritage_ring": {"heritage_ring", "heritage_ne_ring", "heritage", "tourist_core"},
    "nature_daytrip": {"nature_daytrip", "sataplia_nature", "sataplia_tourist", "nature_walk"},
    "regional_attractions": {"regional_attractions", "daytrip", "tourist_core", "nature_walk"},
    "useful_services": {"useful_services"},
}

CATEGORY_COMPATIBILITY: dict[str, set[str]] = {
    "culture": {"culture", "museum", "viewpoint", "walk"},
    "museum": {"museum", "culture"},
    "viewpoint": {"viewpoint", "culture", "walk"},
    "food": {"food", "cafe", "market"},
    "cafe": {"cafe", "food"},
    "market": {"market", "food"},
    "walk": {"walk", "park", "beach", "viewpoint", "culture", "nature"},
    "park": {"park", "walk", "nature"},
    "beach": {"beach", "walk", "nature"},
    "nature": {"nature", "walk", "park", "viewpoint"},
    "transport": {"transport", "culture"},
}

CATEGORY_MATCH_DISTANCE_M = {
    "food": 160.0,
    "cafe": 160.0,
    "market": 180.0,
    "park": 260.0,
    "culture": 420.0,
    "museum": 360.0,
    "viewpoint": 500.0,
    "walk": 650.0,
    "nature": 900.0,
    "beach": 650.0,
    "transport": 260.0,
}

MIN_MUST_HAVE_COVERAGE_RATIO = 0.8


@dataclass(frozen=True)
class CoverageAcceptance:
    """Итоговый verdict готовности города по must-have coverage."""

    city_slug: str | None
    total_critical: int
    matched_critical: int
    explained_critical: int
    unresolved_critical: int
    blocking_critical: int
    coverage_ratio: float
    accepted: bool
    reasons: list[str]

    def as_dict(self) -> dict[str, object]:
        return {
            "city_slug": self.city_slug,
            "total_critical": self.total_critical,
            "matched_critical": self.matched_critical,
            "explained_critical": self.explained_critical,
            "unresolved_critical": self.unresolved_critical,
            "blocking_critical": self.blocking_critical,
            "coverage_ratio": self.coverage_ratio,
            "accepted": self.accepted,
            "reasons": self.reasons,
        }


def scope_aliases(scope: str | None) -> set[str]:
    """Возвращает все совместимые коды scope для нового или legacy-названия."""

    if not scope:
        return set()
    return SCOPE_ALIASES.get(scope, {scope})


def gap_reason_is_explained(reason: str | None) -> bool:
    """True, если gap имеет понятную причину, которую можно показать админу."""

    return bool(reason and reason in EXPLAINED_GAP_REASONS)


def gap_reason_blocks_publication(reason: str | None) -> bool:
    """True, если причина должна блокировать readiness до ручного решения."""

    return bool(reason and reason in BLOCKING_GAP_REASONS)
