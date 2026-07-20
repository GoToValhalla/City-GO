from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from services.place_address_coverage import city_address_report
from services.place_address_flow import run_address_recovery_flow
from services.place_address_policy import is_generic_address, needs_recovery


def test_address_coverage_reports_generic_addresses_new() -> None:
    class P:
        def __init__(self, address: str, category: str):
            self.id = 1
            self.title = "Точка"
            self.address = address
            self.category = category
            self.is_published = True
            self.is_visible_in_catalog = True
            self.is_route_eligible = True
            self.publication_status = "published"

    report = city_address_report([
        P("пляж", "walk"),
        P("набережная", "cafe"),
        P("улица Мира, 1", "food"),
    ])
    assert report["generic_address_count"] == 2
    assert is_generic_address("пляж", "walk")
    assert is_generic_address("набережная", "cafe")
    assert report["literal_placeholder_count"] == 0


def test_address_recovery_flow_dry_run_all_cities_new(
    db_session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    place_factory,
) -> None:
    monkeypatch.chdir(tmp_path)
    place_factory(slug="flow-generic", title="Набережная", category="walk", address="набережная")
    payload = {
        "display_name": "улица Курортная, Зеленоградск",
        "address": {"road": "улица Курортная", "house_number": "2", "city": "Зеленоградск"},
    }
    with patch("services.place_address_recovery.reverse_geocode_payload", return_value=payload):
        result = run_address_recovery_flow(
            db_session,
            city_slugs=None,
            limit=5,
            sleep_seconds=0,
            apply_changes=False,
            include_generic=True,
        )
    assert Path(result["summary_json"]).exists()
    assert result["mode"] == "dry_run"
    assert "coverage_before_json" in result


def test_address_recovery_flow_apply_from_review_only_should_apply_new(
    db_session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    city_factory,
    place_factory,
) -> None:
    monkeypatch.chdir(tmp_path)
    city = city_factory(slug="khanty-mansiysk", name="Ханты-Мансийск")
    place = place_factory(slug="flow-apply", title="Flow Apply", city_id=city.id, address=None)
    payload = {
        "display_name": "улица Мира, 1, Ханты-Мансийск",
        "address": {"road": "улица Мира", "house_number": "1", "city": "Ханты-Мансийск"},
    }
    with patch("services.place_address_recovery.reverse_geocode_payload", return_value=payload):
        result = run_address_recovery_flow(
            db_session,
            city_slugs=["khanty-mansiysk"],
            limit=1,
            sleep_seconds=0,
            apply_changes=True,
            include_generic=False,
        )
    city_result = next(item for item in result["cities"] if item["city_slug"] == "khanty-mansiysk")
    assert city_result["applied"] >= 0
    assert Path(result["summary_json"]).exists()
    db_session.refresh(place)
    assert place.address is not None


def test_address_recovery_flow_does_not_overwrite_real_addresses_new(place_factory) -> None:
    place = place_factory(
        slug="flow-real-address",
        title="Real Address",
        category="food",
        address="улица Мира, 13, Ханты-Мансийск",
    )
    assert needs_recovery(place.address, place.category, include_generic=True) is False


def test_address_recovery_flow_saves_summary_new(
    db_session,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    city_factory,
    place_factory,
) -> None:
    monkeypatch.chdir(tmp_path)
    city = city_factory(slug="kaliningrad", name="Калининград")
    place_factory(slug="flow-summary", title="Summary Place", city_id=city.id, address=None)
    payload = {
        "display_name": "улица Мира, 1, Калининград",
        "address": {"road": "улица Мира", "house_number": "1", "city": "Калининград"},
    }
    with patch("services.place_address_recovery.reverse_geocode_payload", return_value=payload):
        result = run_address_recovery_flow(
            db_session,
            city_slugs=["kaliningrad"],
            limit=1,
            sleep_seconds=0,
            apply_changes=False,
            include_generic=False,
        )
    summary = json.loads(Path(result["summary_json"]).read_text(encoding="utf-8"))
    assert summary["cities"]
    assert summary["coverage_before_json"]


def test_address_recovery_flow_skips_city_only_for_food_new() -> None:
    from services.place_address_recovery_assess import assess_proposed_address

    result = assess_proposed_address("Зеленоградск", "cafe", city_name="Зеленоградск", city_slug="zelenogradsk")
    assert result["should_apply"] is False
    assert result["skip_reason"] == "city_only"


def test_geocoder_user_agent_no_example_com_new(monkeypatch: pytest.MonkeyPatch) -> None:
    from core.config import settings
    from services.place_address_geocode import DEFAULT_USER_AGENT, geocoder_user_agent

    monkeypatch.setattr(settings, "place_address_geocoder_user_agent", "Bad (citygo@example.com)")
    assert geocoder_user_agent() == DEFAULT_USER_AGENT
    assert "example.com" not in geocoder_user_agent().casefold()
