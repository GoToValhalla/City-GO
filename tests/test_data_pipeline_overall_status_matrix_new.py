"""Decision table / equivalence classes для overall_status Data Pipeline."""

from __future__ import annotations

import pytest

from schemas.data_pipeline_status import DataPipelineMetrics
from services.data_pipeline_status.build_status import _degraded_sections, _overall_status
from services.data_pipeline_status.constants import SECTION_LABELS
from services.data_pipeline_status.queues import _row


@pytest.mark.parametrize(
    ("places_total", "degraded", "expected"),
    [
        (0, [], "empty"),
        (0, ["Импорт"], "partial_degraded"),
        (5, [], "healthy"),
        (5, ["Импорт"], "partial_degraded"),
        (5, ["Импорт", "Координаты"], "partial_degraded"),
        (5, ["Импорт", "Координаты", "Проверка мест"], "full_degraded"),
        (5, ["a", "b", "c", "d"], "full_degraded"),
    ],
)
def test_overall_status_decision_table_new(places_total, degraded, expected) -> None:
    metrics = DataPipelineMetrics(places_total=places_total)
    assert _overall_status(metrics, degraded) == expected


@pytest.mark.parametrize(
    ("pending", "running", "failed", "expected_status"),
    [
        (0, 0, 0, "idle"),
        (1, 0, 0, "ok"),
        (10, 0, 0, "ok"),
        (11, 0, 0, "warning"),
        (0, 1, 0, "warning"),
        (0, 0, 1, "error"),
        (5, 2, 1, "error"),
    ],
)
def test_queue_row_boundary_values_new(pending, running, failed, expected_status) -> None:
    row = _row("import", pending, running, failed)
    assert row.status == expected_status
    assert row.pending_count == pending


def test_degraded_sections_equivalence_classes_new() -> None:
    metrics = DataPipelineMetrics(
        places_total=10,
        places_without_coordinates=2,
        open_review_items=1,
        pending_photos=1,
    )
    queues = [
        _row("import", 0, 0, 1),
        _row("enrichment", 12, 0, 0),
        _row("photo_review", 0, 0, 0),
        _row("verification", 0, 0, 0),
    ]
    sections = _degraded_sections(metrics, queues)
    assert SECTION_LABELS["imports"] in sections
    assert SECTION_LABELS["enrichment"] in sections
    assert SECTION_LABELS["photos"] in sections
    assert SECTION_LABELS["verification"] in sections
    assert SECTION_LABELS["coordinates"] in sections
    assert len(sections) >= 3
