from __future__ import annotations

from services.place_address_coverage import city_address_report
from services.place_address_policy import (
    is_generic_address,
    is_placeholder_address,
    is_real_address,
    needs_backfill,
    should_apply_geocode_result,
)


def test_address_coverage_detects_missing_addresses_new():
    class P:
        def __init__(self, address: str | None, category: str = "museum"):
            self.id = 1
            self.title = "Музей"
            self.address = address
            self.category = category
            self.is_route_eligible = True
            self.publication_status = "published"

    report = city_address_report([P("Адрес не указан"), P("улица Ленина, 1")])
    assert report["without_address"] == 1
    assert report["address_not_specified_count"] == 1
    assert report["with_real_address"] == 1


def test_address_coverage_detects_generic_addresses_new():
    class P:
        def __init__(self, address: str, category: str):
            self.id = 1
            self.title = "Точка"
            self.address = address
            self.category = category
            self.is_route_eligible = False
            self.publication_status = "published"

    report = city_address_report([P("центр города", "cafe"), P("променад", "walk")])
    assert report["generic_address_count"] == 2
    assert report["address_unclear_count"] == 1


def test_backfill_does_not_overwrite_existing_address_new():
    assert needs_backfill("улица Ленина, 1") is False
    assert needs_backfill("Адрес не указан") is True


def test_backfill_skips_generic_result_for_food_new():
    assert should_apply_geocode_result("Ханты-Мансийск", "cafe") is False
    assert should_apply_geocode_result("улица Мира, 13", "cafe") is True
    assert is_generic_address("центр города", "cafe") is True
    assert is_generic_address("променад", "walk") is True
    assert is_placeholder_address("Адрес не указан") is True
    assert is_real_address("улица Мира, 13") is True
