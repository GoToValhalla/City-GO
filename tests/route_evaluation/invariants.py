"""Reusable, invariant-based assertions for the CITYGO-358 deterministic
route evaluation dataset.

These check STRUCTURAL PROPERTIES a route must always satisfy (contract,
scope, uniqueness, coordinates, status coherence) — never exact waypoint
identity/order/count, which the task explicitly forbids ("invariant-based
assertions, not exact waypoint snapshots").

A FailureRecord is produced for every violation, matching the exact field
list required by CITYGO-358's "Required failure record" section, so a
violation is always reproducible without re-running anything.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from models.city import City
from models.place import Place
from services.place_public_visibility import PUBLIC_HIDDEN_CATEGORIES
from services.route_finalize_types import FinalRoute


@dataclass
class FailureRecord:
    scenario_id: str
    entrypoint: str
    build_mode: str
    retrieval_strategy: str | None
    expected_status: str
    actual_status: str
    violating_place_ids: list[str] = field(default_factory=list)
    violated_invariant: str = ""
    candidate_counts: dict[str, object] = field(default_factory=dict)
    filter_reason_counts: dict[str, object] = field(default_factory=dict)
    partial_reason: str | None = None
    warnings: list[str] = field(default_factory=list)
    generation_run_id: str = ""
    failure_stage: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "scenario_id": self.scenario_id,
            "entrypoint": self.entrypoint,
            "build_mode": self.build_mode,
            "retrieval_strategy": self.retrieval_strategy,
            "expected_status": self.expected_status,
            "actual_status": self.actual_status,
            "violating_place_ids": self.violating_place_ids,
            "violated_invariant": self.violated_invariant,
            "candidate_counts": self.candidate_counts,
            "filter_reason_counts": self.filter_reason_counts,
            "partial_reason": self.partial_reason,
            "warnings": self.warnings,
            "generation_run_id": self.generation_run_id,
            "failure_stage": self.failure_stage,
        }


class RouteInvariantViolation(AssertionError):
    def __init__(self, record: FailureRecord) -> None:
        self.record = record
        super().__init__(
            f"[{record.scenario_id}/{record.entrypoint}/{record.build_mode}] "
            f"invariant violated: {record.violated_invariant} "
            f"(expected_status={record.expected_status!r} actual_status={record.actual_status!r} "
            f"violating_place_ids={record.violating_place_ids!r})"
        )


def _base_record(
    *,
    scenario_id: str,
    entrypoint: str,
    build_mode: str,
    expected_status: str,
    actual_status: str,
    generation_run_id: str,
    retrieval_strategy: str | None = None,
    partial_reason: str | None = None,
    warnings: list[str] | None = None,
    candidate_counts: dict[str, object] | None = None,
    filter_reason_counts: dict[str, object] | None = None,
) -> FailureRecord:
    return FailureRecord(
        scenario_id=scenario_id,
        entrypoint=entrypoint,
        build_mode=build_mode,
        retrieval_strategy=retrieval_strategy,
        expected_status=expected_status,
        actual_status=actual_status,
        candidate_counts=candidate_counts or {},
        filter_reason_counts=filter_reason_counts or {},
        partial_reason=partial_reason,
        warnings=list(warnings or []),
        generation_run_id=generation_run_id,
        failure_stage="",
    )


def assert_points_satisfy_public_route_contract(
    db: Session,
    points: list[Any],
    *,
    scenario_id: str,
    entrypoint: str,
    build_mode: str,
    expected_status: str,
    actual_status: str,
    generation_run_id: str,
    **record_kwargs: Any,
) -> None:
    """Every returned point must currently match the canonical public route
    SQL contract (same predicates as production public loaders)."""
    if not points:
        return
    from services.route_eligibility import public_route_eligible_sql_conditions

    place_ids = [int(point.place_id) for point in points]
    valid_ids = {
        int(row.id)
        for row in db.query(Place)
        .join(City, Place.city_id == City.id)
        .filter(Place.id.in_(place_ids), *public_route_eligible_sql_conditions())
        .all()
    }
    violating = [str(place_id) for place_id in place_ids if place_id not in valid_ids]
    if violating:
        raise RouteInvariantViolation(
            _with_violation(
                _base_record(
                    scenario_id=scenario_id,
                    entrypoint=entrypoint,
                    build_mode=build_mode,
                    expected_status=expected_status,
                    actual_status=actual_status,
                    generation_run_id=generation_run_id,
                    **record_kwargs,
                ),
                invariant="public_route_contract",
                violating_place_ids=violating,
            )
        )


def _with_violation(record: FailureRecord, *, invariant: str, violating_place_ids: list[str]) -> FailureRecord:
    record.violated_invariant = invariant
    record.violating_place_ids = violating_place_ids
    return record


def assert_correct_city_and_destination_scope(
    points: list[Any],
    *,
    expected_city_slug: str | None,
    scenario_id: str,
    entrypoint: str,
    build_mode: str,
    expected_status: str,
    actual_status: str,
    generation_run_id: str,
    **record_kwargs: Any,
) -> None:
    if not points or expected_city_slug is None:
        return
    violating = [
        str(point.place_id)
        for point in points
        if getattr(point, "city_slug", None) not in (None, expected_city_slug)
    ]
    if violating:
        raise RouteInvariantViolation(
            _with_violation(
                _base_record(
                    scenario_id=scenario_id,
                    entrypoint=entrypoint,
                    build_mode=build_mode,
                    expected_status=expected_status,
                    actual_status=actual_status,
                    generation_run_id=generation_run_id,
                    **record_kwargs,
                ),
                invariant="correct_city_scope",
                violating_place_ids=violating,
            )
        )


def assert_no_duplicate_place_ids(
    points: list[Any],
    *,
    scenario_id: str,
    entrypoint: str,
    build_mode: str,
    expected_status: str,
    actual_status: str,
    generation_run_id: str,
    **record_kwargs: Any,
) -> None:
    seen: set[str] = set()
    duplicates: list[str] = []
    for point in points:
        place_id = str(point.place_id)
        if place_id in seen:
            duplicates.append(place_id)
        seen.add(place_id)
    if duplicates:
        raise RouteInvariantViolation(
            _with_violation(
                _base_record(
                    scenario_id=scenario_id,
                    entrypoint=entrypoint,
                    build_mode=build_mode,
                    expected_status=expected_status,
                    actual_status=actual_status,
                    generation_run_id=generation_run_id,
                    **record_kwargs,
                ),
                invariant="no_duplicate_place_ids",
                violating_place_ids=duplicates,
            )
        )


def assert_no_forbidden_categories(
    points: list[Any],
    *,
    scenario_id: str,
    entrypoint: str,
    build_mode: str,
    expected_status: str,
    actual_status: str,
    generation_run_id: str,
    **record_kwargs: Any,
) -> None:
    violating = [
        str(point.place_id)
        for point in points
        if str(getattr(point, "category", "") or "").strip().lower() in PUBLIC_HIDDEN_CATEGORIES
    ]
    if violating:
        raise RouteInvariantViolation(
            _with_violation(
                _base_record(
                    scenario_id=scenario_id,
                    entrypoint=entrypoint,
                    build_mode=build_mode,
                    expected_status=expected_status,
                    actual_status=actual_status,
                    generation_run_id=generation_run_id,
                    **record_kwargs,
                ),
                invariant="no_forbidden_categories",
                violating_place_ids=violating,
            )
        )


def assert_valid_coordinates(
    points: list[Any],
    *,
    scenario_id: str,
    entrypoint: str,
    build_mode: str,
    expected_status: str,
    actual_status: str,
    generation_run_id: str,
    **record_kwargs: Any,
) -> None:
    violating = [
        str(point.place_id)
        for point in points
        if point.lat is None
        or point.lng is None
        or not (-90.0 <= float(point.lat) <= 90.0)
        or not (-180.0 <= float(point.lng) <= 180.0)
        or (float(point.lat) == 0.0 and float(point.lng) == 0.0)
    ]
    if violating:
        raise RouteInvariantViolation(
            _with_violation(
                _base_record(
                    scenario_id=scenario_id,
                    entrypoint=entrypoint,
                    build_mode=build_mode,
                    expected_status=expected_status,
                    actual_status=actual_status,
                    generation_run_id=generation_run_id,
                    **record_kwargs,
                ),
                invariant="valid_coordinates",
                violating_place_ids=violating,
            )
        )


def assert_zero_points_is_no_route(
    final: FinalRoute | Any,
    *,
    scenario_id: str,
    entrypoint: str,
    build_mode: str,
    generation_run_id: str,
    **record_kwargs: Any,
) -> None:
    points = list(getattr(final, "points", []) or [])
    status = str(getattr(final, "status", ""))
    if not points and status != "no_route":
        raise RouteInvariantViolation(
            _with_violation(
                _base_record(
                    scenario_id=scenario_id,
                    entrypoint=entrypoint,
                    build_mode=build_mode,
                    expected_status="no_route",
                    actual_status=status,
                    generation_run_id=generation_run_id,
                    **record_kwargs,
                ),
                invariant="zero_points_is_no_route",
                violating_place_ids=[],
            )
        )


def assert_one_point_is_never_ready(
    final: FinalRoute | Any,
    *,
    scenario_id: str,
    entrypoint: str,
    build_mode: str,
    generation_run_id: str,
    **record_kwargs: Any,
) -> None:
    points = list(getattr(final, "points", []) or [])
    status = str(getattr(final, "status", ""))
    if len(points) == 1 and status == "ready":
        raise RouteInvariantViolation(
            _with_violation(
                _base_record(
                    scenario_id=scenario_id,
                    entrypoint=entrypoint,
                    build_mode=build_mode,
                    expected_status="partial_route",
                    actual_status=status,
                    generation_run_id=generation_run_id,
                    **record_kwargs,
                ),
                invariant="one_point_never_ready",
                violating_place_ids=[str(points[0].place_id)],
            )
        )


_KNOWN_STATUSES = frozenset({"no_route", "partial_route", "ready", "failed", "preview", "preview_failed"})


def assert_status_warnings_partial_reason_coherent(
    final: FinalRoute | Any,
    *,
    scenario_id: str,
    entrypoint: str,
    build_mode: str,
    generation_run_id: str,
    **record_kwargs: Any,
) -> None:
    status = str(getattr(final, "status", ""))
    partial_reason = getattr(final, "partial_reason", None)
    points = list(getattr(final, "points", []) or [])

    if status not in _KNOWN_STATUSES:
        raise RouteInvariantViolation(
            _with_violation(
                _base_record(
                    scenario_id=scenario_id,
                    entrypoint=entrypoint,
                    build_mode=build_mode,
                    expected_status="<one of known statuses>",
                    actual_status=status,
                    generation_run_id=generation_run_id,
                    partial_reason=partial_reason,
                    **record_kwargs,
                ),
                invariant="status_is_a_known_value",
                violating_place_ids=[],
            )
        )
    if status == "ready" and partial_reason is not None:
        raise RouteInvariantViolation(
            _with_violation(
                _base_record(
                    scenario_id=scenario_id,
                    entrypoint=entrypoint,
                    build_mode=build_mode,
                    expected_status="ready",
                    actual_status=status,
                    generation_run_id=generation_run_id,
                    partial_reason=partial_reason,
                    **record_kwargs,
                ),
                invariant="ready_status_must_have_no_partial_reason",
                violating_place_ids=[str(p.place_id) for p in points],
            )
        )
    if status == "no_route" and points:
        raise RouteInvariantViolation(
            _with_violation(
                _base_record(
                    scenario_id=scenario_id,
                    entrypoint=entrypoint,
                    build_mode=build_mode,
                    expected_status="no_route",
                    actual_status=status,
                    generation_run_id=generation_run_id,
                    partial_reason=partial_reason,
                    **record_kwargs,
                ),
                invariant="no_route_status_must_have_no_points",
                violating_place_ids=[str(p.place_id) for p in points],
            )
        )


def run_all_point_invariants(
    db: Session,
    final: FinalRoute | Any,
    *,
    scenario_id: str,
    entrypoint: str,
    build_mode: str,
    expected_status: str,
    expected_city_slug: str | None,
    generation_run_id: str,
    retrieval_strategy: str | None = None,
) -> None:
    """Runs every per-point + per-route invariant this dataset requires, in
    one call, so a scenario test body stays a single readable line."""
    points = list(getattr(final, "points", []) or [])
    actual_status = str(getattr(final, "status", ""))
    kwargs = dict(
        retrieval_strategy=retrieval_strategy,
        partial_reason=getattr(final, "partial_reason", None),
        warnings=list(getattr(final, "warnings", []) or []),
    )

    assert_zero_points_is_no_route(
        final, scenario_id=scenario_id, entrypoint=entrypoint, build_mode=build_mode,
        generation_run_id=generation_run_id, **kwargs,
    )
    assert_one_point_is_never_ready(
        final, scenario_id=scenario_id, entrypoint=entrypoint, build_mode=build_mode,
        generation_run_id=generation_run_id, **kwargs,
    )
    assert_status_warnings_partial_reason_coherent(
        final, scenario_id=scenario_id, entrypoint=entrypoint, build_mode=build_mode,
        generation_run_id=generation_run_id, **kwargs,
    )
    assert_points_satisfy_public_route_contract(
        db, points, scenario_id=scenario_id, entrypoint=entrypoint, build_mode=build_mode,
        expected_status=expected_status, actual_status=actual_status,
        generation_run_id=generation_run_id, **kwargs,
    )
    assert_correct_city_and_destination_scope(
        points, expected_city_slug=expected_city_slug, scenario_id=scenario_id, entrypoint=entrypoint,
        build_mode=build_mode, expected_status=expected_status, actual_status=actual_status,
        generation_run_id=generation_run_id, **kwargs,
    )
    assert_no_duplicate_place_ids(
        points, scenario_id=scenario_id, entrypoint=entrypoint, build_mode=build_mode,
        expected_status=expected_status, actual_status=actual_status,
        generation_run_id=generation_run_id, **kwargs,
    )
    assert_no_forbidden_categories(
        points, scenario_id=scenario_id, entrypoint=entrypoint, build_mode=build_mode,
        expected_status=expected_status, actual_status=actual_status,
        generation_run_id=generation_run_id, **kwargs,
    )
    assert_valid_coordinates(
        points, scenario_id=scenario_id, entrypoint=entrypoint, build_mode=build_mode,
        expected_status=expected_status, actual_status=actual_status,
        generation_run_id=generation_run_id, **kwargs,
    )
