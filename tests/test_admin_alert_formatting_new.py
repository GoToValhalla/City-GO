from services.admin_alert_service import _format_alert_text


def test_enrichment_finished_alert_is_human_readable_new():
    text = _format_alert_text(
        title="Enrichment pipeline finished",
        message="Зеленоградск готов к проверке после обогащения. Мест обработано: 253.",
        level="info",
        city_slug="zelenogradsk",
        job_id=9,
        details={
            "status": "success",
            "source": "admin_city_enrichment",
            "places_total": 253,
            "readiness": {
                "readiness_score": 64,
                "status": "needs_review",
                "components": {
                    "places_total": 253,
                    "places_active": 6,
                    "eligible_places": 192,
                    "photo_coverage_pct": 5.9,
                    "address_coverage_pct": 95.3,
                    "description_coverage_pct": 100.0,
                    "hours_any_pct": 34.8,
                    "route_eligibility_pct": 75.9,
                    "verification_coverage_pct": 0.0,
                },
            },
        },
    )

    assert "City GO: Обогащение завершено" in text
    assert "Город прошел обогащение и ждет ручной проверки." in text
    assert "Итог: readiness 64/100, статус: нужна проверка" in text
    assert "Места: всего 253, активных 6, для маршрутов 192" in text
    assert "Покрытие: адреса 95.3%, фото 5.9%, описания 100%" in text
    assert "Что дальше: добавить фото, проверить места, добить часы работы." in text
    assert "details:" not in text
    assert '"components"' not in text


def test_stalled_import_alert_explains_next_action_new():
    text = _format_alert_text(
        title="Import job stalled",
        message="Import job stopped sending heartbeat and was marked as stalled.",
        level="error",
        city_slug="astrakhan",
        job_id=2,
        details={
            "job_id": 2,
            "city_slug": "astrakhan",
            "source": "admin_city_enrichment",
            "last_error": "Import job stalled: no heartbeat before timeout",
        },
    )

    assert "City GO: Задача импорта зависла" in text
    assert "Worker не обновлял прогресс дольше порога" in text
    assert "Тип задачи: обогащение данных" in text
    assert "Что дальше: после деплоя фикса нажать «Повторить»" in text
    assert "details:" not in text
