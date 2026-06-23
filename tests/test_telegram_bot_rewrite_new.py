from datetime import datetime

from models.place_field_confidence import PlaceFieldConfidence
from models.route import Route
from models.route_place import RoutePlace
from telegram_bot.callbacks import cb
from telegram_bot.quality import is_hours_reliable, is_place_bot_visible, is_technical_osm_title
from telegram_bot.renderers import place_card_text
from telegram_bot.schemas import BotPlace
from telegram_bot.services.facade import BotFacade
from telegram_bot.session import get_or_create_session, get_short_id, resolve_short_id, toggle_favorite


def test_callback_data_stays_under_telegram_limit_new() -> None:
    samples = [
        cb("m", "main"),
        cb("c", "set", "khanty-mansiysk"),
        cb("r", "view", "a1B2"),
        cb("r", "go", "a1B2"),
        cb("rn", "pt", 12),
        cb("p", "cat", "sights", 3),
        cb("p", "view", "a1B2"),
        cb("near", "list", "coffee", 2),
        cb("open", "list", 1),
        cb("fav", "toggle", "p", "a1B2"),
    ]

    assert all(len(item.encode("utf-8")) <= 64 for item in samples)


def test_technical_osm_titles_are_hidden_new() -> None:
    assert is_technical_osm_title("node/123456")
    assert is_technical_osm_title("Культурное место OSM 15446204")
    assert is_technical_osm_title("Место для прогулки OSM 1492576554")
    assert not is_technical_osm_title("Археопарк")


def test_service_category_is_not_bot_visible_new(place_factory) -> None:
    service = place_factory(title="Банк", category="service")
    park = place_factory(title="Археопарк", category="park")

    assert is_place_bot_visible(service) is False
    assert is_place_bot_visible(park) is True


def test_low_stale_conflict_hours_are_not_reliable_new() -> None:
    high = PlaceFieldConfidence(place_id=1, field_name="opening_hours", confidence=0.9,
                                confidence_level="high", freshness_status="fresh", conflict_status="none")
    low = PlaceFieldConfidence(place_id=1, field_name="opening_hours", confidence=0.3,
                               confidence_level="low", freshness_status="fresh", conflict_status="none")
    stale = PlaceFieldConfidence(place_id=1, field_name="opening_hours", confidence=0.9,
                                 confidence_level="high", freshness_status="stale", conflict_status="none")
    conflict = PlaceFieldConfidence(place_id=1, field_name="opening_hours", confidence=0.9,
                                    confidence_level="high", freshness_status="fresh", conflict_status="conflict")

    assert is_hours_reliable(high) is True
    assert is_hours_reliable(low) is False
    assert is_hours_reliable(stale) is False
    assert is_hours_reliable(conflict) is False


def test_place_card_does_not_render_debug_fields_or_placeholder_new() -> None:
    text = place_card_text(
        BotPlace(
            id=1,
            title="node/123",
            category="park",
            short_description="Хорошее место для прогулки.",
            address="ул. Мира, 1",
            hours_reliable=False,
            opening_hours_display="Mo-Fr 09:00-18:00",
        )
    )

    assert "node/123" not in text
    assert "Без названия" in text
    assert "confidence" not in text.lower()
    assert "source" not in text.lower()
    assert "Mo-Fr" not in text


def test_facade_filters_non_tourist_and_technical_places_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="bot-city")
    visible = place_factory(city_id=city.id, title="Археопарк", category="park")
    place_factory(city_id=city.id, title="Культурное место OSM 15446204", category="culture")
    place_factory(city_id=city.id, title="Отдел МВД", category="service")

    page = BotFacade(db_session).places_by_category("bot-city", "sights")

    assert [item.id for item in page.items] == [visible.id]


def test_route_with_less_than_two_valid_points_is_unavailable_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="route-city")
    place = place_factory(city_id=city.id, title="Парк", category="park", is_route_eligible=True)
    route = Route(city_id=city.id, slug="single-point", title="Одна точка", is_active=True)
    db_session.add(route)
    db_session.commit()
    db_session.refresh(route)
    db_session.add(RoutePlace(route_id=route.id, place_id=place.id, position=1))
    db_session.commit()

    assert BotFacade(db_session).route(route.id) is None


def test_session_short_ids_and_favorites_new(db_session) -> None:
    session = get_or_create_session(db_session, 123, "tester")
    short = get_short_id(session, 987)

    assert resolve_short_id(session, short) == 987
    assert toggle_favorite(session, "p", 987) is True
    assert 987 in session.favorites["places"]
    assert toggle_favorite(session, "p", 987) is False
    assert 987 not in session.favorites["places"]
