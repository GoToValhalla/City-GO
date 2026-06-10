"""Сохранение route_generation_runs и candidates."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from models.route_generation_candidate import RouteGenerationCandidate
from models.route_generation_run import RouteGenerationRun
from services.route_eligibility import ALGORITHM_VERSION
from services.route_generation_diagnostics.candidate_audit import AuditedCandidate


def persist_generation_run(
    db: Session,
    *,
    city_id: int | None,
    user_id: int | None,
    request_json: dict[str, Any],
    status: str,
    failure_reason: str | None,
    audited: list[AuditedCandidate],
    selected_place_ids: set[int],
    scores_by_place_id: dict[int, float] | None = None,
    selection_reasons_by_place_id: dict[int, list[str]] | None = None,
    commit: bool = True,
) -> RouteGenerationRun:
    total = len(audited)
    eligible = sum(1 for row in audited if row.is_eligible)
    run = RouteGenerationRun(
        city_id=city_id,
        user_id=user_id,
        request_json=request_json,
        status=status,
        failure_reason=failure_reason,
        algorithm_version=ALGORITHM_VERSION,
        total_candidates=total,
        eligible_candidates=eligible,
        selected_places=len(selected_place_ids),
    )
    db.add(run)
    db.flush()
    scores = scores_by_place_id or {}
    selections = selection_reasons_by_place_id or {}
    for row in audited:
        place_id = row.place.id
        selected = place_id in selected_place_ids
        db.add(RouteGenerationCandidate(
            generation_run_id=run.id,
            place_id=place_id,
            is_eligible=row.is_eligible,
            score=scores.get(place_id, row.score),
            selected=selected,
            rejection_reasons=list(row.rejection_reasons) if row.rejection_reasons else None,
            selection_reasons=selections.get(place_id) if selected else None,
        ))
    if commit:
        db.commit()
        db.refresh(run)
    return run
