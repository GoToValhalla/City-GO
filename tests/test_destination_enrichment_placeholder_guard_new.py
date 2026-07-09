from __future__ import annotations

from models.data_foundation import EnrichmentTask
from services.destination_enrichment_pipeline import _missing_changes
from services.place_data_merge_service import PlaceDataMergeService
from services.place_data_sanitizer import is_placeholder_enrichment_value
from data.scripts.audit_placeholder_enrichment import audit_placeholder_enrichment


PLACEHOLDER_ADDRESS = "Адрес уточнён по контуру направления"
PLACEHOLDER_HOURS = {"text": "Время работы уточняется"}


def _task_for_place(db_session, place, changes: dict[str, object]) -> EnrichmentTask:
    task = EnrichmentTask(
        city_id=place.city_id,
        place_id=place.id,
        task_type="destination_deterministic_enrichment",
        status="completed",
        payload={"changes": changes, "source": "EXTERNAL_API_ENRICHED", "confidence": 0.82},
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)
    return task


def test_missing_changes_returns_no_fabricated_data_for_empty_place(db_session, place_factory):
    place = place_factory(title="Музей моря", address=None)
    place.short_description = None
    place.opening_hours = None
    place.average_visit_duration_minutes = None
    db_session.commit()

    assert _missing_changes(place) == {}


def test_placeholder_detector_catches_legacy_values():
    assert is_placeholder_enrichment_value("address", PLACEHOLDER_ADDRESS)
    assert is_placeholder_enrichment_value("opening_hours", PLACEHOLDER_HOURS)
    assert is_placeholder_enrichment_value("short_description", "Музей моря — место в направлении City GO.", title="Музей моря")


def test_merge_skips_placeholder_address(db_session, place_factory):
    place = place_factory(title="Музей моря", address=None)
    task = _task_for_place(db_session, place, {"address": PLACEHOLDER_ADDRESS})

    result = PlaceDataMergeService().merge_from_enrichment_task(db_session, task.id, actor="test")

    db_session.refresh(place)
    assert result["status"] == "skipped"
    assert result["reason"] == "no_safe_changes"
    assert place.address is None


def test_merge_skips_placeholder_opening_hours(db_session, place_factory):
    place = place_factory(title="Музей моря")
    place.opening_hours = None
    db_session.commit()
    task = _task_for_place(db_session, place, {"opening_hours": PLACEHOLDER_HOURS})

    result = PlaceDataMergeService().merge_from_enrichment_task(db_session, task.id, actor="test")

    db_session.refresh(place)
    assert result["status"] == "skipped"
    assert result["reason"] == "no_safe_changes"
    assert place.opening_hours is None


def test_merge_skips_placeholder_description(db_session, place_factory):
    place = place_factory(title="Музей моря")
    place.short_description = None
    db_session.commit()
    task = _task_for_place(db_session, place, {"short_description": "Музей моря — место в направлении City GO."})

    result = PlaceDataMergeService().merge_from_enrichment_task(db_session, task.id, actor="test")

    db_session.refresh(place)
    assert result["status"] == "skipped"
    assert result["reason"] == "no_safe_changes"
    assert place.short_description is None


def test_audit_placeholder_enrichment_is_read_only_and_reports_counts(db_session, place_factory):
    clean = place_factory(title="Чистое место", address="Набережная, 1")
    polluted_address = place_factory(title="Плохой адрес", address=PLACEHOLDER_ADDRESS)
    polluted_hours = place_factory(title="Плохие часы", address="Улица, 2")
    polluted_hours.opening_hours = PLACEHOLDER_HOURS
    polluted_description = place_factory(title="Плохое описание", address="Улица, 3")
    polluted_description.short_description = "Плохое описание — место в направлении City GO."
    db_session.commit()

    report = audit_placeholder_enrichment(db_session, limit_ids=10)

    db_session.refresh(clean)
    db_session.refresh(polluted_address)
    db_session.refresh(polluted_hours)
    db_session.refresh(polluted_description)
    assert clean.address == "Набережная, 1"
    assert polluted_address.address == PLACEHOLDER_ADDRESS
    assert polluted_hours.opening_hours == PLACEHOLDER_HOURS
    assert polluted_description.short_description == "Плохое описание — место в направлении City GO."
    assert report["mode"] == "read_only"
    assert report["total_matches"] == 3
    assert report["fields"]["address"]["count"] == 1
    assert report["fields"]["opening_hours"]["count"] == 1
    assert report["fields"]["short_description"]["count"] == 1
