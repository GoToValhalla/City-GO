from services.admin_alert_service import _format_alert_text


def test_import_warning_alert_lists_failed_steps_in_russian_new() -> None:
    text = _format_alert_text(
        title="Import completed with warnings",
        message="Полный импорт завершён, но некоторые этапы требуют внимания.",
        level="warning",
        city_slug="rostov-on-don",
        job_id=7,
        details={
            "status": "success_with_warnings",
            "source": "admin_city_import",
            "places_total": 3592,
            "warnings": [
                {"step": "finding_images", "error": "Провайдер фотографий недоступен"},
                {"step": "source_enrichment", "error": "Ошибок этапов обогащения: 1"},
            ],
        },
    )
    assert "Импорт завершён с предупреждениями" in text
    assert "завершено с предупреждениями" in text
    assert "Мест в городе: 3592" in text
    assert "поиск фотографий: Провайдер фотографий недоступен" in text
    assert "обогащение внешними источниками: Ошибок этапов обогащения: 1" in text
    assert "Что дальше:" in text


def test_import_success_alert_has_readiness_and_no_warning_section_new() -> None:
    text = _format_alert_text(
        title="Import pipeline finished",
        message="Ростов-на-Дону готов к проверке.",
        level="info",
        city_slug="rostov-on-don",
        job_id=8,
        details={
            "status": "success",
            "source": "admin_city_import",
            "places_total": 3592,
            "readiness": {"readiness_score": 72},
            "warnings": [],
        },
    )
    assert "Импорт завершён" in text
    assert "Готовность города: 72/100" in text
    assert "Предупреждения:" not in text


def test_unified_import_suppresses_intermediate_completion_alert_new() -> None:
    source = open("services/admin_city_import_job_service.py", encoding="utf-8").read()
    assert "notify_completion=False" in source
    assert "unified_pipeline" in source
    assert '"completed":True' in source.replace(" ", "")
    assert "unified_import_pipeline_finished" in source
