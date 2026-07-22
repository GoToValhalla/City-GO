from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from services.data_quality.readiness import diagnostic_gates


@dataclass(frozen=True)
class QualityEvaluationResult:
    status: str
    blocks_publication: bool
    failed_gates: tuple[str, ...]


def evaluate_city_quality(db: Session, *, city_id: int, city_slug: str) -> QualityEvaluationResult:
    payload = diagnostic_gates(db, city_id=city_id, city_slug=city_slug)
    return QualityEvaluationResult(
        status=str(payload["status"]),
        blocks_publication=bool(payload["blocks_publication"]),
        failed_gates=tuple(map(str, payload["failed_gates"])),
    )
