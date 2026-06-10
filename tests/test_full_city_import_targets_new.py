"""Проверка import targets для full city import run."""

from __future__ import annotations

import json
from pathlib import Path

from data.scripts.import_cron_config import load_targets

EXPECTED = {
    "almaty",
    "yerevan",
    "zelenogradsk",
    "kaliningrad",
    "kutaisi",
    "rostov-on-don",
    "khanty-mansiysk",
}


def test_import_targets_cover_all_cities_new() -> None:
    targets = load_targets(Path("data/config/import_targets.json"))
    cities = {target["city"] for target in targets}
    assert EXPECTED.issubset(cities)


def test_kaliningrad_and_almaty_have_scopes_new() -> None:
    payload = json.loads(Path("data/config/import_targets.json").read_text(encoding="utf-8"))
    by_city = {item["city"]: item["scopes"] for item in payload["targets"]}
    assert len(by_city["kaliningrad"]) >= 3
    assert len(by_city["almaty"]) >= 3
