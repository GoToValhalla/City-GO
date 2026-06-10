from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class CoverageGateThresholds:
    min_total_places: int = 80
    min_coordinates_ratio: float = 0.95
    min_opening_hours_ratio: float = 0.70
    min_visit_duration_ratio: float = 0.80
    required_categories: tuple[str, ...] = ("coffee", "food", "walk", "museum", "bar", "park")


@dataclass(frozen=True)
class CoverageGateResult:
    passed: bool
    failures: tuple[str, ...] = ()


def evaluate_coverage_gate(
    report: Mapping[str, object],
    thresholds: CoverageGateThresholds = CoverageGateThresholds(),
) -> CoverageGateResult:
    total = _int_field(report, "total_places")
    category_counts = _category_counts(report)
    failures = (
        _min_total_failure(total, thresholds),
        _ratio_failure(report, "with_coordinates", total, thresholds.min_coordinates_ratio),
        _ratio_failure(report, "with_opening_hours", total, thresholds.min_opening_hours_ratio),
        _ratio_failure(report, "with_visit_duration", total, thresholds.min_visit_duration_ratio),
        _required_categories_failure(category_counts, thresholds.required_categories),
    )
    compact_failures = tuple(filter(None, failures))
    return CoverageGateResult(passed=len(compact_failures) == 0, failures=compact_failures)


def _min_total_failure(total: int | None, thresholds: CoverageGateThresholds) -> str | None:
    if total is None:
        return "total_places is missing or invalid"
    if total < thresholds.min_total_places:
        return f"total_places {total} is below {thresholds.min_total_places}"
    return None


def _ratio_failure(
    report: Mapping[str, object],
    field: str,
    total: int | None,
    minimum: float,
) -> str | None:
    value = _int_field(report, field)
    if value is None:
        return f"{field} is missing or invalid"
    ratio = 0.0 if total in (None, 0) else value / total
    if ratio < minimum:
        return f"{field} ratio {ratio:.3f} is below {minimum:.3f}"
    return None


def _required_categories_failure(
    category_counts: Mapping[str, int],
    required_categories: tuple[str, ...],
) -> str | None:
    missing = tuple(filter(lambda category: category_counts.get(category, 0) <= 0, required_categories))
    if not missing:
        return None
    return "required categories missing: " + ", ".join(missing)


def _int_field(report: Mapping[str, object], field: str) -> int | None:
    value = report.get(field)
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _category_counts(report: Mapping[str, object]) -> Mapping[str, int]:
    value = report.get("category_counts")
    if not isinstance(value, dict):
        return {}
    return dict(filter(lambda item: isinstance(item[0], str) and _is_count(item[1]), value.items()))


def _is_count(value: object) -> bool:
    return not isinstance(value, bool) and isinstance(value, int)
