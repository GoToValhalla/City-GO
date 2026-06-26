from __future__ import annotations

from datetime import UTC, datetime, timedelta

from scripts.refresh_all_cities import CityMetrics, CityRun, RefreshReport, format_report, split_telegram_text


def test_refresh_report_contains_city_quality_delta() -> None:
    before = CityMetrics(
        slug="astrakhan",
        name="Астрахань",
        total=10,
        with_address=4,
        with_photo=1,
    )
    after = CityMetrics(
        slug="astrakhan",
        name="Астрахань",
        total=13,
        with_address=9,
        with_photo=2,
        published=3,
        visible=4,
        route_eligible=5,
        needs_publication_review=6,
        unverified=7,
        readiness_score=64,
        quality_status="needs_review",
    )
    city = CityRun(slug="astrakhan", name="Астрахань", before=before, after=after)
    city.add_scope_result({"created": 3, "updated": 2, "unchanged": 5, "rejected": 1, "hidden": 0, "missing_from_source": 2})
    city.coverage_summary = {"matched": 8, "unresolved": 2, "critical_unresolved": 1}
    city.coverage_acceptance = {"accepted": False, "reason": "critical gaps"}

    report = RefreshReport(
        started_at=datetime(2026, 6, 26, 10, 0, tzinfo=UTC),
        finished_at=datetime(2026, 6, 26, 10, 2, 5, tzinfo=UTC),
        dry_run=False,
        city_filter=None,
        city_runs=[city],
    )

    text = format_report(report)

    assert "✅ CITY GO · ОБНОВЛЕНИЕ ГОРОДОВ" in text
    assert "Итого добавлено: 3" in text
    assert "🏙 Астрахань (astrakhan)" in text
    assert "Места: 10 → 13 (+3)" in text
    assert "С адресами: 9/13" in text
    assert "С фото: 2/13" in text
    assert "На публикационную проверку: 6" in text
    assert "Coverage: matched=8; unresolved=2; critical=1" in text


def test_refresh_report_shows_failures() -> None:
    city = CityRun(
        slug="kutaisi",
        name="Кутаиси",
        before=CityMetrics(slug="kutaisi", name="Кутаиси"),
        after=CityMetrics(slug="kutaisi", name="Кутаиси"),
    )
    city.failures.append({"scope": "tourist_core", "profile": "tourist_core", "error": "overpass timeout"})
    report = RefreshReport(
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC) + timedelta(seconds=1),
        dry_run=True,
        city_filter="kutaisi",
        city_runs=[city],
    )

    text = format_report(report)

    assert "⚠️ CITY GO · ОБНОВЛЕНИЕ ГОРОДОВ" in text
    assert "Ошибок: 1" in text
    assert "tourist_core/tourist_core: overpass timeout" in text


def test_telegram_split_keeps_long_report_sendable() -> None:
    text = "\n".join(f"line {index}" for index in range(1000))

    chunks = split_telegram_text(text, limit=1000)

    assert len(chunks) > 1
    assert all(len(chunk) <= 1000 for chunk in chunks)
