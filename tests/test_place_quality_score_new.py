"""Тесты Place Quality Score."""

from __future__ import annotations

from models.place import Place
from services.place_quality_score import compute_place_quality_score, is_low_quality, quality_bucket


def _place(**kwargs) -> Place:
    defaults = dict(
        city_id=1, slug="q1", title="Q", lat=43.2, lng=76.9, category="museum",
        is_active=True, status="active", verification_status="unverified",
    )
    defaults.update(kwargs)
    return Place(**defaults)


def test_full_place_high_score_new() -> None:
    score = compute_place_quality_score(_place(
        image_url="http://x.jpg", address="ул. Абая", short_description="Музей",
        opening_hours={"mon": "10-18"}, source_url="http://m.kz", verification_status="verified",
    ))
    assert score == 100
    assert quality_bucket(score) == "high"
    assert not is_low_quality(score)


def test_minimal_place_low_score_new() -> None:
    score = compute_place_quality_score(_place(image_url=None, address=None, short_description=None))
    assert score == 15
    assert quality_bucket(score) == "low"
    assert is_low_quality(score)
