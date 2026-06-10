from telegram_bot.services.context_summary import format_context_snapshot


def test_format_context_snapshot_with_route() -> None:
    text = format_context_snapshot(
        {
            "has_location": True,
            "raw_address": "Зеленоградск",
            "has_route": True,
            "route_points": 3,
        }
    )

    assert "Геолокация: <b>есть</b>" in text
    assert "Адрес: <b>Зеленоградск</b>" in text
    assert "Маршрут: <b>есть, 3 точек</b>" in text
