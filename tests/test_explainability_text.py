from services.explainability_text import point_phrase, warning_phrase


def test_point_phrase_uses_russian_forms() -> None:
    assert point_phrase(1) == "1 точку"
    assert point_phrase(2) == "2 точки"
    assert point_phrase(5) == "5 точек"
    assert point_phrase(11) == "11 точек"


def test_warning_phrase_separates_point_and_route_warnings() -> None:
    assert warning_phrase(2, 3) == (
        "Есть предупреждения по 2 точкам и 1 предупреждение по маршруту."
    )
    assert warning_phrase(1, 1) == "Есть предупреждения по 1 точке."
    assert warning_phrase(0, 2) == "Есть 2 предупреждения по маршруту."
