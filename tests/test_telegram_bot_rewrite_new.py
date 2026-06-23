from datetime import datetime

from models.place_field_confidence import PlaceFieldConfidence
from models.route import Route
from models.route_place import RoutePlace
from models.route_session import RouteSession, RouteSessionPoint
from telegram_bot.callbacks import cb, parse_callback
from telegram_bot.handlers.catalog import _route_state_from_backend, _should_push_nav
from telegram_bot.keyboards.catalog import favorites_list, request_location, route_step
from telegram_bot.quality import is_hours_reliable, is_non_tourist_category, is_place_bot_visible, is_technical_osm_title
from telegram_bot.renderers import nearby_request_text, place_card_text, places_list_text, route_step_text
from telegram_bot.schemas import BotPlace, BotRoute, BotRoutePoint
from telegram_bot.services.facade import BotFacade
from telegram_bot.session import get_or_create_session, get_short_id, pop_nav, push_nav, resolve_short_id, toggle_favorite


def test_callback_data_stays_under_telegram_limit_new() -> None:
    samples = [
        cb("m", "main"),
        cb("c", "set", "khanty-mansiysk"),
        cb("r", "view", "a1B2"),
        cb("r", "go", "a1B2"),
        cb("rn", "pt", 12),
        cb("rn", "skip", 12),
        cb("p", "cat", "sights", 3),
        cb("p", "view", "a1B2"),
        cb("near", "list", "coffee", 2),
        cb("open", "list", 1),
        cb("fav", "add", "p", "a1B2"),
        cb("fav", "del", "r", "a1B2"),
        cb("fav", "toggle", "p", "a1B2"),
    ]

    assert all(len(item.encode("utf-8")) <= 64 for item in samples)


def test_action_callbacks_do_not_pollute_back_stack_new() -> None:
    assert _should_push_nav("back", parse_callback("back")) is False
    assert _should_push_nav("fav:add:p:a1B2", parse_callback("fav:add:p:a1B2")) is False
    assert _should_push_nav("fav:del:r:a1B2", parse_callback("fav:del:r:a1B2")) is False
    assert _should_push_nav("rn:visit:0", parse_callback("rn:visit:0")) is False
    assert _should_push_nav("rn:skip:0", parse_callback("rn:skip:0")) is False
    assert _should_push_nav("rn:pt:1", parse_callback("rn:pt:1")) is False
    assert _should_push_nav("r:view:a1B2", parse_callback("r:view:a1B2")) is True
    assert _should_push_nav("p:cat:sights:0", parse_callback("p:cat:sights:0")) is True
    assert _should_push_nav("fav:list", parse_callback("fav:list")) is True


def test_nearby_request_uses_inline_fallback_not_broken_location_keyboard_new() -> None:
    text = nearby_request_text()
    keyboard = request_location()
    callbacks = [button.callback_data for row in keyboard.inline_keyboard for button in row if button.callback_data]

    assert "скрепку" in text
    assert "p:cat:sights:0" in callbacks
    assert "p:cat:food:0" in callbacks
    assert "p:cat:all:0" in callbacks
    assert all(getattr(button, "request_location", None) is None for row in keyboard.inline_keyboard for button in row)


def test_telegram_route_state_keeps_backend_session_id_new() -> None:
    backend_session = RouteSession(
        id=77,
        route_id=12,
        status="active",
        current_point_index=1,
        visited_point_indexes=[0],
        skipped_point_indexes=[],
        started_at=datetime.utcnow(),
    )
    backend_session.points = [
        RouteSessionPoint(session_id=77, place_id=1, ordering_index=0, title="Парк"),
        RouteSessionPoint(session_id=77, place_id=2, ordering_index=1, title="Музей"),
    ]

    state = _route_state_from_backend(backend_session)

    assert state["route_id"] == 12
    assert state["session_id"] == 77
    assert state["current_index"] == 1
    assert state["visited"] == [0]
    assert state["skipped"] == []


def test_route_step_keyboard_has_explicit_skip_new() -> None:
    point = BotRoutePoint(index=0, place_id=1, title="Парк", lat=54.9, lng=20.4)

    keyboard = route_step(point, 3, False)
    callbacks = [button.callback_data for row in keyboard.inline_keyboard for button in row if button.callback_data]

    assert "rn:visit:0" in callbacks
    assert "rn:skip:0" in callbacks
    assert "rn:pt:1" in callbacks


def test_route_step_text_explains_visited_and_skipped_new() -> None:
    point = BotRoutePoint(index=1, place_id=2, title="Музей", category="museum", address="ул. Ленина, 1")
    route = BotRoute(id=2, title="Маршрут", points=[BotRoutePoint(index=0, place_id=1, title="Парк"), point])

    text = route_step_text(route, point, visited_count=1, skipped_count=1)

    assert "Посещено: 1. Пропущено: 1." in text
    assert "🏛 Музей" in text


def test_technical_osm_titles_are_hidden_new() -> None:
    assert is_technical_osm_title("node/123456")
    assert is_technical_osm_title("Культурное место OSM 15446204")
    assert is_technical_osm_title("Место для прогулки OSM 1492576554")
    assert not is_technical_osm_title("Археопарк")


def test_non_tourist_category_variants_are_filtered_new() -> None:
    assert is_non_tourist_category("service")
    assert is_non_tourist_category("services")
    assert is_non_tourist_category("STOP")
    assert is_non_tourist_category(" pharmacy ")
    assert not is_non_tourist_category("park")


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


def test_places_list_explains_category_distance_and_address_new() -> None:
    text = places_list_text(
        "📍 Рядом",
        [BotPlace(id=1, title="Парк", category="park", address="ул. Мира, 1", distance_m=240)],
        0,
    )

    assert "🌿 Парк" in text
    assert "240 м" in text
    assert "ул. Мира" in text
    assert "Открой карточку" in text


def test_facade_filters_non_tourist_and_technical_places_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="bot-city")
    visible = place_factory(city_id=city.id, title="Археопарк", category="park")
    place_factory(city_id=city.id, title="Культурное место OSM 15446204", category="culture")
    place_factory(city_id=city.id, title="Отдел МВД", category="service")

    page = BotFacade(db_session).places_by_category("bot-city", "sights")

    assert [item.id for item in page.items] == [visible.id]


def test_facade_city_picker_matches_website_available_cities_new(db_session, city_factory) -> None:
    published = city_factory(slug="published-city", name="Опубликованный", launch_status="published")
    ready = city_factory(slug="ready-city", name="Готовый", launch_status="ready")
    hidden = city_factory(slug="draft-city", name="Черновик", launch_status="draft")

    cities = BotFacade(db_session).published_cities()
    slugs = {city.slug for city in cities}

    assert published.slug in slugs
    assert ready.slug not in slugs
    assert hidden.slug not in slugs


def test_facade_category_groups_cover_common_food_and_sights_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="category-city")
    restaurant = place_factory(city_id=city.id, title="Ресторан", category="restaurant")
    monument = place_factory(city_id=city.id, title="Памятник", category="monument")

    food = BotFacade(db_session).places_by_category(city.slug, "food")
    sights = BotFacade(db_session).places_by_category(city.slug, "sights")

    assert [item.id for item in food.items] == [restaurant.id]
    assert [item.id for item in sights.items] == [monument.id]


def test_facade_finds_city_by_slug_or_name_text_new(db_session, city_factory) -> None:
    city = city_factory(slug="zelenogradsk-text", name="Зеленоградск")
    facade = BotFacade(db_session)

    assert facade.city_by_text("zelenogradsk-text") == facade.city(city.slug)
    assert facade.city_by_text("Зеленоградск") == facade.city(city.slug)
    assert facade.city_by_text("Зелен") == facade.city(city.slug)


def test_facade_nearby_skips_far_places_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="nearby-city")
    visible = place_factory(city_id=city.id, title="Парк", category="park", lat=54.9611, lng=20.4703)
    place_factory(city_id=city.id, title="Далеко", category="park", lat=55.9611, lng=21.4703)

    places = BotFacade(db_session).nearby_places("nearby-city", 54.9611, 20.4703)

    assert [item.id for item in places] == [visible.id]


def test_published_city_count_matches_website_available_city_count_new(db_session, city_factory, place_factory) -> None:
    city = city_factory(slug="count-city")
    place_factory(city_id=city.id, title="Археопарк", category="park")
    place_factory(city_id=city.id, title="Сервисный центр", category="service")
    place_factory(city_id=city.id, title="Культурное место OSM 15446204", category="culture")

    city_card = BotFacade(db_session).city("count-city")

    assert city_card is not None
    assert city_card.places_count == 3


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


def test_favorites_keyboard_opens_saved_entities_new(db_session) -> None:
    session = get_or_create_session(db_session, 222, "tester")
    route = BotRoute(id=10, title="Маршрут")
    place = BotPlace(id=20, title="Парк")

    keyboard = favorites_list([route], [place], session)
    callbacks = [button.callback_data for row in keyboard.inline_keyboard for button in row if button.callback_data]

    assert any(item and item.startswith("r:view:") for item in callbacks)
    assert any(item and item.startswith("p:view:") for item in callbacks)


def test_session_short_ids_and_favorites_new(db_session) -> None:
    session = get_or_create_session(db_session, 123, "tester")
    short = get_short_id(session, 987)

    assert resolve_short_id(session, short) == 987
    assert toggle_favorite(session, "p", 987) is True
    assert 987 in session.favorites["places"]
    assert toggle_favorite(session, "p", 987) is False
    assert 987 not in session.favorites["places"]


def test_nav_stack_returns_to_previous_screen_new(db_session) -> None:
    session = get_or_create_session(db_session, 124, "tester")

    push_nav(session, "m:main")
    push_nav(session, "r:list:0")
    push_nav(session, "r:view:a1B2")

    assert pop_nav(session) == "r:list:0"
    assert pop_nav(session) == "m:main"
    assert pop_nav(session) is None
