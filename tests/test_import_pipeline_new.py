"""Тесты import pipeline и slug."""

from services.import_pipeline.steps import STEP_LABELS, STEP_READY_FOR_REVIEW
from services.slug_transliterate import transliterate_cyrillic


def test_transliterate_almaty_new() -> None:
    assert transliterate_cyrillic("Алматы") == "almaty"


def test_step_labels_russian_new() -> None:
    assert "Собираем" in STEP_LABELS["collecting_places"]
    assert STEP_LABELS[STEP_READY_FOR_REVIEW] == "Готово к проверке"
