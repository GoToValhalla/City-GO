# City GO Telegram Bot

Last updated: 2026-07-01

The Telegram bot is a lightweight tourist interface over the same City GO data quality rules as the web product. It must be presentable, short, and safe: no raw OSM ids, no service-category trash, no debug labels, no unreliable open-now answers.

## Goals

The bot supports the key website functionality in Telegram:

- city selection;
- main menu;
- routes;
- route detail;
- lightweight route mode;
- categories and places;
- nearby places via Telegram location;
- open now;
- favorites;
- text search;
- help and fallback states.
- place moderation for admins when the feature toggle is enabled.

The bot does not try to replace a full interactive map. It links out to external maps for place/route point navigation.

## Runtime

Code location:

```text
telegram_bot/
```

Entrypoints:

```text
telegram_bot_main.py             Polling process used by docker-compose bot service
telegram_bot/main.py             Bot, dispatcher, middleware, polling/webhook feed
routers/telegram_bot_webhook.py  FastAPI webhook endpoint
```

Token behavior:

- preferred: `BOT_TOKEN`;
- fallback: `TELEGRAM_BOT_TOKEN`;
- webhook endpoint accepts either.

Docker service:

```text
docker-compose.yml → service: bot
```

## Modules

```text
telegram_bot/callbacks.py          callback_data builder/parser
telegram_bot/session.py            bot_sessions repository helpers, nav stack, short ids, favorites
telegram_bot/quality.py            final quality filters for bot visibility
telegram_bot/renderers.py          HTML message rendering and fallbacks
telegram_bot/keyboards/catalog.py  inline/reply keyboards
telegram_bot/handlers/admin_moderation.py  admin place moderation callbacks
telegram_bot/services/facade.py    BotFacade over ORM and quality gates
telegram_bot/handlers/catalog.py   /start, menu, callbacks, route mode, places, search, location
telegram_bot/analytics.py          bot_events logger
```

Route mode also uses the shared backend route-session service:

```text
models/route_session.py
services/route_session_service.py
```

Admin analytics:

```text
routers/admin_bot_analytics.py
services/admin_bot_analytics_service.py
```

## Database

Tables:

```text
bot_sessions
bot_events
route_sessions
route_session_points
```

`bot_sessions` stores Telegram UI/session context:

- `telegram_user_id`
- `username`
- `selected_city_slug`
- `current_flow`
- `last_message_id`
- `nav_stack`
- `short_ids`
- `route_session`
- `favorites`
- `last_location`

`bot_sessions.route_session` stores a lightweight pointer/state snapshot:

- route id;
- backend route session id;
- current index;
- visited indexes;
- skipped indexes;
- started_at.

`route_sessions` and `route_session_points` store durable route progress shared with future web navigation.

`bot_events` stores product analytics:

- bot started;
- city selected;
- route viewed/started/completed;
- route point visited/skipped;
- place viewed;
- nearby used;
- open-now used;
- search query;
- no-result search;
- favorite added/removed.

## User Flows

### Keyboard Contract

The production main menu is inline-only. The bot may send
`ReplyKeyboardRemove` to hide old persistent keyboards, but it must not use
`ReplyKeyboardMarkup` for the main menu. Native location request keyboards are
allowed only in flows where Telegram location is explicitly needed.

Slash commands such as `/start`, `/menu`, `/help`, and `/moderation` are handled
by command routers and are ignored by the generic text fallback.

### Start

`/start`:

- if the user already has a valid selected city, the bot opens that city menu;
- if one public city exists, the bot immediately selects it and shows main menu;
- if multiple public cities exist, it shows city selection with place counts;
- if none exist, it shows an honest empty state without an empty inline keyboard.

Public city means:

- `City.is_active = true`
- `City.launch_status` is one of `published`, `auto_published`, `limited_published`, `ready`, `ready_for_review`, `review`, `needs_review`, `enriched`, `launch_ready`.

If no city is selected yet, a free-text message can select a public city by slug or name match before falling back to the city selector.

### Main Menu

Buttons:

- `🚶 Маршруты`
- `📍 Места рядом`
- `👀 Что посмотреть`
- `☕ Еда и кофе`
- `🕐 Открыто сейчас`
- `❤️ Избранное`
- `🏙 Сменить город`
- `❓ Помощь`

When global feature toggle `telegram_admin_moderation` is enabled, admins also
see:

- `🛠 Модерация`

The button uses callback data only and does not carry secrets.

### Admin Moderation

`/moderation` and `🛠 Модерация` open the same place review flow when
`telegram_admin_moderation` is enabled. When the toggle is disabled, the command
answers: `Модерация временно выключена`.

The flow:

- shows cities with review/rejected counters;
- opens one place card;
- supports publish, reject, move to queue end, next, back to cities;
- supports restoring rejected places to the review queue.

Publishing delegates to shared backend review logic and its publication blockers.
Telegram does not duplicate safety rules and does not pass admin tokens through
messages, callback data, deep links, or web app query strings.

### Routes

Route list returns only active routes with at least two bot-eligible points.

Route card shows:

- title;
- description;
- time/distance/point count if present;
- first route points;
- start button;
- all-points button;
- external map button if a point has coordinates;
- favorite button;
- back/menu.

### Route Mode

Route mode starts by creating a backend `route_sessions` record through `services.route_session_service.start_route_session()`.

Controls:

- `Я на месте`;
- `Пропустить точку`;
- `Предыдущая`;
- `Следующая`;
- `На карте`;
- `Завершить`;
- `В меню`.

Behavior:

- `Я на месте` calls backend check-in with action `visit` and advances to the next open point;
- `Пропустить точку` calls backend check-in with action `skip` and advances to the next open point;
- `Предыдущая` / `Следующая` update current point index without marking a point visited;
- `Завершить` completes backend route session;
- route-point visits/skips and route completion are logged to `bot_events`;
- old Telegram route session dicts without `session_id` still degrade through the legacy in-session flow.

If the user sent Telegram location earlier, route step text includes distance to the current point. If there is no GPS, route mode remains manual.

### Places

Category place lists use `BotFacade.places_by_category()` and `telegram_bot.quality.is_place_bot_visible()`.

The main category groups intentionally cover common real taxonomy aliases:

- sights: culture, museum, park, walk, viewpoint, beach, attraction, landmark, historic, monument, art, architecture;
- food: food, coffee, cafe, restaurant, bar, bakery, fast_food, ice_cream.

Place list rows show category, distance when known, and address when available. Place card shows:

- clean title;
- human category label;
- short description;
- address if available;
- reliable hours only;
- distance if known;
- map/favorite/similar/back buttons.

If the photo is invalid or Telegram fails to send it, the bot falls back to a text card.

### Nearby

If user sends location:

- save `last_location` in session;
- query places within 3 km;
- sort by distance;
- show only bot-visible places with coordinates.

Nearby category callbacks are parsed as `near:list:{category}:{page}`. The current implementation returns the first distance-sorted page from the stored location.

### Favorites

Favorites are stored in `bot_sessions.favorites`. The favorites screen renders saved routes and places as clickable buttons, so the user can open the saved entity directly instead of seeing a dead text list.

## Verification

Targeted tests:

```bash
.venv/bin/python -m pytest --no-cov tests/test_telegram_bot_rewrite_new.py -q
```

Relevant deploy checks:

```bash
python -m py_compile telegram_bot/handlers/catalog.py telegram_bot/services/facade.py telegram_bot/renderers.py telegram_bot/keyboards/catalog.py
```
# Геопозиция

Основной bot flow хранит pending intent (`nearby`, `build_route`,
`continue_route`) с TTL. Reply-кнопка отправляет native Telegram location.
Точная позиция имеет отдельный TTL, после Nearby очищается и не включается в
analytics/log payload. При отсутствии позиции доступны центр выбранного города
и смена города. Полный контракт: [Location and Map Platform](location_and_map_platform.md).
