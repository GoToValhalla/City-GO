"""
tests/test_osm_address_parser_new.py

5 тестов для расширенного парсера адресов OSM.
Все тесты юнит, без обращений к БД.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Импорт private-функции из скрипта (sys.path гарантирован PYTHONPATH)
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data.scripts.import_city_osm import _address  # type: ignore[attr-defined]


def test_street_house_city():
    """Стандартный addr: набор — собирает полный адрес."""
    tags = {
        "addr:street": "ул. Пушкина",
        "addr:housenumber": "10",
        "addr:city": "Зеленоградск",
    }
    assert _address(tags) == "ул. Пушкина, 10, Зеленоградск"


def test_contact_street_and_housenumber():
    """contact: теги работают как альтернатива addr: тегам."""
    tags = {
        "contact:street": "Курортный пр.",
        "contact:housenumber": "5а",
    }
    assert _address(tags) == "Курортный пр., 5а"


def test_addr_place_without_street():
    """addr:place используется если нет addr:street."""
    tags = {
        "addr:place": "Центральный парк",
        "addr:city": "Светлогорск",
    }
    assert _address(tags) == "Центральный парк, Светлогорск"


def test_addr_full_fallback():
    """addr:full возвращается когда нет structured данных."""
    tags = {
        "addr:full": "Россия, Зеленоградск, ул. Ленина, д. 1",
    }
    assert _address(tags) == "Россия, Зеленоградск, ул. Ленина, д. 1"


def test_contact_address_fallback():
    """contact:address — ещё один fallback для полного адреса."""
    tags = {
        "contact:address": "Зеленоградск, пр. Ленина 3",
    }
    assert _address(tags) == "Зеленоградск, пр. Ленина 3"


def test_no_address_tags_returns_none():
    """При отсутствии всех адресных тегов возвращается None."""
    tags = {"name": "Кафе Морской", "amenity": "cafe"}
    assert _address(tags) is None


def test_addr_town_used_as_city_fallback():
    """addr:town используется если addr:city отсутствует."""
    tags = {
        "addr:street": "ул. Садовая",
        "addr:housenumber": "7",
        "addr:town": "Пионерский",
    }
    assert _address(tags) == "ул. Садовая, 7, Пионерский"


def test_structured_takes_priority_over_full():
    """Structured address приоритетнее addr:full."""
    tags = {
        "addr:street": "ул. Ленина",
        "addr:housenumber": "1",
        "addr:full": "Неточный полный адрес",
    }
    result = _address(tags)
    assert result == "ул. Ленина, 1"
    assert "Неточный" not in result
