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


# --- CITYGO-265: category-profile fabrication (atmosphere/inside/best_for) --


def test_placeholder_detector_catches_former_category_profile_values_new() -> None:
    """The now-removed _category_profile() (services/place_enrichment_sources.py)
    generated these exact strings per category group -- kept in the sanitizer
    purely for historical-row detection, not regenerated."""
    assert is_placeholder_enrichment_value("atmosphere", "Еда и отдых")
    assert is_placeholder_enrichment_value("inside", "Экспозиции, архитектурные детали или исторический контекст")
    assert is_placeholder_enrichment_value("best_for", "Прогулка, фото и спокойный маршрут")


def test_placeholder_detector_does_not_flag_a_genuine_atmosphere_value_new() -> None:
    assert not is_placeholder_enrichment_value("atmosphere", "Уютная веранда с видом на залив")


def test_audit_placeholder_enrichment_reports_polluted_category_profile_fields_new(db_session, place_factory):
    clean = place_factory(title="Настоящая атмосфера", address="Улица, 4")
    clean.atmosphere = "Уютная веранда с видом на залив"
    polluted = place_factory(title="Выдуманная атмосфера", address="Улица, 5")
    polluted.atmosphere = "Еда и отдых"
    polluted.inside = "Зал, меню и возможность сделать паузу"
    polluted.best_for = "Кофе, перекус или спокойная остановка в маршруте"
    db_session.commit()

    report = audit_placeholder_enrichment(db_session, limit_ids=10)

    db_session.refresh(clean)
    db_session.refresh(polluted)
    assert clean.atmosphere == "Уютная веранда с видом на залив"
    assert report["fields"]["atmosphere"]["count"] == 1
    assert polluted.id in report["fields"]["atmosphere"]["place_ids"]
    assert report["fields"]["inside"]["count"] == 1
    assert report["fields"]["best_for"]["count"] == 1


def test_audit_placeholder_enrichment_flags_fabricated_confidence_rows_new(db_session, place_factory):
    """Rows in place_field_confidence tagged source_type="citygo_category_rules"
    are a durable historical marker even if the field itself was later
    edited by an admin and no longer holds the exact fabricated string."""
    from models.place_field_confidence import PlaceFieldConfidence

    place = place_factory(title="Место с историей", address="Улица, 6")
    db_session.add(PlaceFieldConfidence(
        place_id=place.id, field_name="atmosphere", confidence=0.55,
        source_type="citygo_category_rules", raw_value={"value": "Еда и отдых"},
    ))
    db_session.commit()

    report = audit_placeholder_enrichment(db_session, limit_ids=10)

    assert report["fabricated_confidence_source_type"] == "citygo_category_rules"
    assert report["fabricated_confidence_rows"]["atmosphere"]["count"] == 1
    assert place.id in report["fabricated_confidence_rows"]["atmosphere"]["place_ids"]
    assert report["total_fabricated_confidence_rows"] == 1


def test_audit_placeholder_enrichment_suspects_former_category_lookup_values_new(db_session, place_factory):
    """average_visit_duration_minutes/price_level had no lineage tracking, so
    an exact-value-per-category match against the removed lookup table is
    the best available historical signal -- explicitly reported as a
    heuristic (possible false positive), separate from the proven matches
    above."""
    suspected = place_factory(title="Подозрительная длительность", address="Улица, 7", category="museum")
    suspected.average_visit_duration_minutes = 75  # former _visit_duration()["museum"]
    suspected.price_level = 1  # former _price_level()["museum"]
    db_session.commit()

    report = audit_placeholder_enrichment(db_session, limit_ids=10)

    assert report["suspected_category_lookup_fields"]["average_visit_duration_minutes"]["count"] == 1
    assert suspected.id in report["suspected_category_lookup_fields"]["average_visit_duration_minutes"]["place_ids"]
    assert report["suspected_category_lookup_fields"]["price_level"]["count"] == 1
    assert report["total_suspected_category_lookup_matches"] == 2
