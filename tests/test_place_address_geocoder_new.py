from __future__ import annotations

import csv
from pathlib import Path
from unittest.mock import patch

import pytest

from core.config import settings
from services.place_address_geocode import DEFAULT_USER_AGENT, geocoder_user_agent
from services.place_address_recovery_assess import assess_proposed_address
from services.place_address_recovery_export import export_review


def test_nominatim_user_agent_has_no_example_com_new(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "place_address_geocoder_user_agent", "CityGoAddressBackfill/1.0")
    ua = geocoder_user_agent()
    assert ua
    assert "example.com" not in ua.casefold()
    assert "CityGo" in ua or "CityGoAddressBackfill" in ua


def test_nominatim_user_agent_rejects_example_com_setting_new(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "place_address_geocoder_user_agent", "Bad/1.0 (contact: citygo@example.com)")
    assert geocoder_user_agent() == DEFAULT_USER_AGENT


def test_address_recovery_export_review_csv_new(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    rows = [{
        "place_id": 1, "slug": "test", "title": "Кафе", "category": "cafe",
        "lat": 61.0, "lng": 69.0, "old_address": "", "proposed_address": "улица Мира 1",
        "source": "nominatim_reverse", "confidence": "medium", "raw_display_name": "raw",
        "should_apply": True, "skip_reason": "", "comment": "ok",
    }]
    summary = {"city": "khanty-mansiysk", "checked": 1, "recoverable": 1, "should_apply_count": 1}
    files = export_review("khanty-mansiysk", rows, summary)
    csv_path = Path(files["csv"])
    assert csv_path.exists()
    with csv_path.open(encoding="utf-8") as handle:
        data = list(csv.DictReader(handle))
    assert data[0]["proposed_address"] == "улица Мира 1"
    assert Path(files["json"]).exists()


def test_address_recovery_marks_generic_as_skip_new() -> None:
    result = assess_proposed_address(
        "Ханты-Мансийск", "cafe", city_name="Ханты-Мансийск", city_slug="khanty-mansiysk",
    )
    assert result["should_apply"] is False
    assert result["skip_reason"] == "city_only"


def test_address_recovery_dry_run_does_not_modify_db_new(
    db_session,
    city_factory,
    place_factory,
) -> None:
    from services.place_address_policy import needs_backfill
    from services.place_address_recovery import run_recovery_dry_run

    city = city_factory(slug="khanty-mansiysk", name="Ханты-Мансийск")
    first = place_factory(slug="dry-run-1", title="Dry Run 1", city_id=city.id, address=None)
    second = place_factory(slug="dry-run-2", title="Dry Run 2", city_id=city.id, address=None)
    payload = {
        "display_name": "улица Мира, Ханты-Мансийск",
        "address": {"road": "улица Мира", "house_number": "1", "city": "Ханты-Мансийск"},
    }
    before = {
        place.id: place.address
        for place in (first, second)
        if needs_backfill(place.address)
    }
    with patch("services.place_address_recovery.reverse_geocode_payload", return_value=payload):
        result = run_recovery_dry_run(
            db_session,
            city_slug="khanty-mansiysk",
            limit=2,
            sleep_seconds=0,
            export_review_files=False,
        )
    after = {
        place.id: place.address
        for place in (first, second)
        if place.id in before
    }
    assert result["checked"] == 2
    assert before == after
