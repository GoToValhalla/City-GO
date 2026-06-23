from models.place_field_confidence import PlaceFieldConfidence
from telegram_bot.handlers.catalog import _generated_route_from_state, _route_state_from_generated
from telegram_bot.keyboards.catalog import generated_route_card
from telegram_bot.renderers import open_now_fallback_text
from telegram_bot.schemas import BotPlace, BotRoute, BotRoutePoint
from telegram_bot.services.facade import BotFacade


def test_generated_route_callbacks_stay_under_telegram_limit_new() -> None:
    route = BotRoute(
        id=0,
        title="Прогулка",
        points=[
            BotRoutePoint(index=0, place_id=1, title="Парк", lat=54.9, lng=20.4),
            BotRoutePoint(index=1, place_id=2, title="Музей", lat=54.91, lng=20.41),
        ],
    )

    keyboard = generated_route_card(route)
    callbacks = [button.callback_data for row in keyboard.inline_keyboard for button in row if button.callback_data]

    assert "r:ggo" in callbacks
    assert "r:gpts" in callbacks
    assert all(len(item.encode("utf-8")) <= 64 for item in callbacks)


def test_generated_route_state_roundtrip_new() -> None:
    route = BotRoute(
        id=0,
        title="Прогулка по городу",
        short_description="Временный маршрут",
        duration_minutes=45,
        distance_km=2.1,
        points=[
            BotRoutePoint(index=0, place_id=1, title="Парк", category="park", lat=54.9, lng=20.4),
            BotRoutePoint(index=1, place_id=2, title="Музей", category="museum", lat=54.91, lng=20.41),
        ],
    )

    state = _route_state_from_generated(route)
    restored = _generated_route_from_state(state)

    assert state["generated"] is True
    assert restored is not None
    assert restored.title == route.title
    assert [point.title for point in restored.points] == ["Парк", "Музей"]


def test_facade_generated_route_filters_service_places_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="telegram-generated-route")
    park = place_factory(city_id=city.id, title="Городской парк", category="park", lat=54.9611, lng=20.4703, is_route_eligible=True)
    museum = place_factory(city_id=city.id, title="Музей", category="museum", lat=54.9621, lng=20.4713, is_route_eligible=True)
    place_factory(city_id=city.id, title="Банк", category="service", lat=54.9631, lng=20.4723, is_route_eligible=True)

    route = BotFacade(db_session).generated_route(city.slug)

    assert route is not None
    assert [point.place_id for point in route.points] == [park.id, museum.id]
    assert "Банк" not in [point.title for point in route.points]


def test_reliable_hours_fallback_uses_only_high_medium_hours_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="telegram-open-now-fallback")
    reliable = place_factory(city_id=city.id, title="Кафе с расписанием", category="cafe")
    reliable.opening_hours = {"display": "10:00-22:00"}
    low = place_factory(city_id=city.id, title="Кафе без доверия", category="cafe")
    low.opening_hours = {"display": "10:00-22:00"}
    db_session.add_all([
        PlaceFieldConfidence(place_id=reliable.id, field_name="opening_hours", confidence=0.9, confidence_level="high", freshness_status="fresh", conflict_status="none"),
        PlaceFieldConfidence(place_id=low.id, field_name="opening_hours", confidence=0.2, confidence_level="low", freshness_status="fresh", conflict_status="none"),
    ])
    db_session.commit()

    page = BotFacade(db_session).reliable_hours_places(city.slug)

    assert [place.id for place in page.items] == [reliable.id]


def test_open_now_fallback_text_is_explicit_new() -> None:
    city = type("CityLike", (), {"name": "Астрахань"})()
    text = open_now_fallback_text(
        city,
        [BotPlace(id=1, title="Кафе", category="cafe", opening_hours_display="10:00-22:00", hours_reliable=True)],
    )

    assert "Точно открытых прямо сейчас не нашёл" in text
    assert "Кафе" in text
