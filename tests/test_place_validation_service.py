"""
Юнит-тесты services.place_validation_service.validate_place.

Проверяются только коды issues и is_valid; сервис не фильтрует объекты pipeline.
"""

from __future__ import annotations

from types import SimpleNamespace

from services.place_validation_service import validate_place


def _place(**kwargs):
    """Минимальный duck-typing stand-in для ORM Place в тестах."""
    defaults = dict(
        lat=54.96,
        lng=20.48,
        opening_hours=None,
        average_visit_duration_minutes=30,
        category="cafe",
        price_level=1,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_validate_place_fully_valid() -> None:
    result = validate_place(_place())
    assert result["is_valid"] is True
    assert result["issues"] == []


def test_validate_place_coordinates_boundary_ok() -> None:
    result = validate_place(_place(lat=90.0, lng=180.0))
    assert result["is_valid"] is True


def test_validate_place_lat_none() -> None:
    result = validate_place(_place(lat=None))
    assert result["is_valid"] is False
    assert "lat_missing" in result["issues"]


def test_validate_place_lng_none() -> None:
    result = validate_place(_place(lng=None))
    assert result["is_valid"] is False
    assert "lng_missing" in result["issues"]


def test_validate_place_lat_out_of_range_high() -> None:
    result = validate_place(_place(lat=91.0))
    assert "lat_out_of_range" in result["issues"]


def test_validate_place_lat_out_of_range_low() -> None:
    result = validate_place(_place(lat=-90.1))
    assert "lat_out_of_range" in result["issues"]


def test_validate_place_lng_out_of_range_high() -> None:
    result = validate_place(_place(lng=180.1))
    assert "lng_out_of_range" in result["issues"]


def test_validate_place_lng_out_of_range_low() -> None:
    result = validate_place(_place(lng=-180.01))
    assert "lng_out_of_range" in result["issues"]


def test_validate_place_lat_invalid_type_bool() -> None:
    result = validate_place(_place(lat=True))
    assert "lat_invalid_type" in result["issues"]


def test_validate_place_opening_hours_none_ok() -> None:
    result = validate_place(_place(opening_hours=None))
    assert result["is_valid"] is True


def test_validate_place_opening_hours_valid_dict() -> None:
    oh = {"mon": {"open": "09:00", "close": "18:00"}, "tue": None}
    result = validate_place(_place(opening_hours=oh))
    assert result["is_valid"] is True


def test_validate_place_opening_hours_invalid_top_level_type() -> None:
    result = validate_place(_place(opening_hours=[]))
    assert "opening_hours_invalid_type" in result["issues"]


def test_validate_place_opening_hours_day_not_dict() -> None:
    result = validate_place(_place(opening_hours={"mon": "closed"}))
    assert "opening_hours_day_invalid" in result["issues"]


def test_validate_place_opening_hours_time_not_string() -> None:
    result = validate_place(_place(opening_hours={"mon": {"open": 9, "close": "18:00"}}))
    assert "opening_hours_time_not_string" in result["issues"]


def test_validate_place_opening_hours_unknown_key() -> None:
    result = validate_place(_place(opening_hours={"mon": {"open": "10:00", "close": "11:00", "lunch": "13:00"}}))
    assert "opening_hours_unknown_key" in result["issues"]


def test_validate_place_opening_hours_unparseable_time() -> None:
    result = validate_place(_place(opening_hours={"mon": {"open": "99:99", "close": "18:00"}}))
    assert "opening_hours_unparseable_time" in result["issues"]


def test_validate_place_visit_duration_none_ok() -> None:
    result = validate_place(_place(average_visit_duration_minutes=None))
    assert result["is_valid"] is True


def test_validate_place_visit_duration_zero() -> None:
    result = validate_place(_place(average_visit_duration_minutes=0))
    assert "visit_duration_non_positive" in result["issues"]


def test_validate_place_visit_duration_negative() -> None:
    result = validate_place(_place(average_visit_duration_minutes=-10))
    assert "visit_duration_non_positive" in result["issues"]


def test_validate_place_visit_duration_invalid_type() -> None:
    result = validate_place(_place(average_visit_duration_minutes="30"))
    assert "visit_duration_invalid_type" in result["issues"]


def test_validate_place_category_empty_string() -> None:
    result = validate_place(_place(category=""))
    assert "category_empty" in result["issues"]


def test_validate_place_category_none_ok() -> None:
    result = validate_place(_place(category=None))
    assert result["is_valid"] is True


def test_validate_place_price_level_none_ok() -> None:
    result = validate_place(_place(price_level=None))
    assert result["is_valid"] is True


def test_validate_place_price_level_out_of_range_high() -> None:
    result = validate_place(_place(price_level=4))
    assert "price_level_out_of_range" in result["issues"]


def test_validate_place_price_level_out_of_range_low() -> None:
    result = validate_place(_place(price_level=-1))
    assert "price_level_out_of_range" in result["issues"]


def test_validate_place_price_level_invalid_type_bool() -> None:
    result = validate_place(_place(price_level=True))
    assert "price_level_invalid_type" in result["issues"]


def test_validate_place_multiple_issues_accumulate() -> None:
    result = validate_place(
        _place(
            lat=None,
            lng=None,
            category="",
            price_level=10,
            average_visit_duration_minutes=0,
            opening_hours="broken",
        )
    )
    assert result["is_valid"] is False
    assert len(result["issues"]) >= 5


def test_validate_place_return_keys() -> None:
    result = validate_place(_place())
    assert set(result.keys()) == {"is_valid", "issues"}
