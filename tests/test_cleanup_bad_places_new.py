from __future__ import annotations

from types import SimpleNamespace

from data.scripts.cleanup_bad_places import is_bad_place


def test_is_bad_place_new_hides_gazprom_station() -> None:
    place = SimpleNamespace(title="Газпром", category="useful")

    assert is_bad_place(place) is True


def test_is_bad_place_new_keeps_real_cafe() -> None:
    place = SimpleNamespace(title="Coffee Like", category="cafe")

    assert is_bad_place(place) is False


def test_is_bad_place_new_hides_technical_category() -> None:
    place = SimpleNamespace(title="Парковка у вокзала", category="parking")

    assert is_bad_place(place) is True
