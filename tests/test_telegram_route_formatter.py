from telegram_bot.services.route_formatter import format_route_message


def test_format_route_message_with_titles_and_warning() -> None:
    text = format_route_message(
        {
            "total_places": 1,
            "total_estimated_minutes": 35,
            "estimated_distance": 1.2,
            "warnings": ["Проверьте часы работы."],
            "points": [
                {
                    "place_id": "7",
                    "visit_minutes": 25,
                    "estimated_walk_minutes": 10,
                }
            ],
        },
        {"7": "Кафе"},
    )
    assert "Маршрут собран с нюансами" in text
    assert "Кафе" in text
    assert "Проверьте часы работы." in text


def test_format_route_message_with_point_time_and_warning() -> None:
    text = format_route_message(
        {
            "total_places": 1,
            "total_estimated_minutes": 35,
            "estimated_distance": 1.2,
            "points": [
                {
                    "place_id": "7",
                    "visit_minutes": 25,
                    "estimated_walk_minutes": 10,
                    "estimated_arrival_time": "2026-05-26T10:15:00",
                    "estimated_departure_time": "2026-05-26T10:40:00",
                    "time_warning": "Часы работы неизвестны.",
                }
            ],
        },
        {"7": "Кафе"},
    )

    assert "10:15-10:40" in text
    assert "Важно: Часы работы неизвестны." in text


def test_format_route_message_empty_route() -> None:
    text = format_route_message({"points": [], "warnings": []}, {})
    assert "Маршрут не собрался" in text


def test_format_route_message_uses_structured_warnings_and_quality() -> None:
    text = format_route_message(
        {
            "total_places": 2,
            "total_estimated_minutes": 90,
            "quality_score": 0.82,
            "user_warnings": [
                {
                    "user_message": "Часы одного места указаны приблизительно.",
                }
            ],
            "points": [{"place_id": "1", "visit_minutes": 30, "estimated_walk_minutes": 5}],
        },
        {"1": "Променад"},
    )
    assert "Качество маршрута: <b>82%</b>" in text
    assert "Часы одного места указаны приблизительно." in text
