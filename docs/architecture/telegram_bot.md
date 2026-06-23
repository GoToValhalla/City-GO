# City GO Telegram Bot

Last updated: 2026-06-23

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

The bot does not try to replace a full interactive map. It links out to external maps for place/route point navigation.

## Runtime

Code location:

```text
telegram_bot/
```

Entrypoints:

```text
telegram_bot_main.py          Polling process used by docker-compose bot service
telegram_bot/main.py          Bot, dispatcher, middleware, polling/webhook feed
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
telegram_bot/services/facade.py    BotFacade over ORM and quality gates
telegram_bot/handlers/catalog.py   /start, menu, callbacks, route mode, places, search, location
telegram_bot/analytics.py          bot_events logger
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
```

`bot_sessions` stores:

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

`bot_events` stores product analytics:

- bot started;
- city selected;
- route viewed/started/completed;
- route point visited;
- place viewed;
- nearby used;
- open-now used;
- search query;
- no-result search;
- favorite added/removed.

## User Flows

### Start

`/start`:

- if one published city exists, the bot immediately selects it and shows main menu;
- if multiple published cities exist, it shows city selection;
- if none exist, it shows an honest empty state.

Published city means:

- `City.is_active = true`
- `City.launch_status = published`

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

Route mode is stored inside `bot_sessions.route_session`.

State includes:

- route id;
- current index;
- visited indexes;
- started_at.

Controls:

- `Я на месте`;
- `Предыдущая`;
- `Следующая`;
- `На карте`;
- `Завершить`;
- `В меню`.

If the user sent Telegram location earlier, route step text includes distance to the current point. If there is no GPS, route mode remains manual.

### Places

Category place lists use `BotFacade.places_by_category()` and `telegram_bot.quality.is_place_bot_visible()`.

Place card shows:

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

If location is missing, bot shows the location request button.

### Open Now

Open-now uses only places where opening hours confidence is reliable:

- `confidence_level in {high, medium}`;
- `freshness_status != stale`;
- `conflict_status is none/null`.

Low/stale/conflict/unknown hours are excluded.

### Search

Any free text outside command/help/menu context is a search query.

Search behavior:

- stores `current_flow = search:{query}`;
- supports pagination through `p:src:{page}`;
- logs `search_query`;
- logs `search_no_results` when empty.

## Callback Contract

Telegram callback_data limit is 64 bytes. Never place UUIDs or long strings directly into callback_data.

Pattern examples:

```text
m:main
c:list
c:set:{slug}
r:list:{page}
r:view:{short_id}
r:go:{short_id}
r:pts:{short_id}
rn:pt:{idx}
rn:visit:{idx}
rn:done
p:cat:{code}:{page}
p:view:{short_id}
p:src:{page}
near:ask
near:list:{cat}:{page}
open:list:{page}
fav:add:p:{short_id}
fav:del:p:{short_id}
fav:add:r:{short_id}
fav:del:r:{short_id}
back
help
```

`fav:toggle` is still supported for old already-rendered messages, but new keyboards must use explicit `add`/`del`.

## Quality Gates

A place is visible in bot lists only if:

- active;
- not spam;
- published;
- visible in catalog;
- publication status is `published`, `auto_published`, or `limited_published`;
- title is not technical;
- category is not blacklisted.

Blacklisted bot categories:

```text
service, bank, atm, mvd, police, government, transport,
hospital, health, medical, pharmacy, military, cemetery,
industrial, waste_disposal, fuel, parking, car_service
```

Technical title examples:

```text
node/123
way/123
relation/123
OSM 123
Культурное место OSM 15446204
Место для прогулки OSM 1492576554
```

## Admin Analytics

Endpoint:

```http
GET /admin/telegram-bot/analytics?days=7
```

Returns:

- `active_users`;
- `events_total`;
- `events_by_type`;
- `top_cities`;
- `route_funnel.started`;
- `route_funnel.completed`;
- `route_funnel.completion_rate_percent`;
- `search_no_results`;
- `latest_events`.

No-result searches are a content backlog source.

## Rate Limit

`SoftRateLimitMiddleware` allows 30 events per user per 60 seconds.

If exceeded:

- callback gets a short answer: `Не так быстро. Подожди пару секунд и нажми снова.`;
- message gets the same text as a reply.

## Verification

```bash
.venv/bin/python -m pytest --no-cov \
  tests/test_telegram_bot_rewrite_new.py \
  tests/test_telegram_bot_completion_new.py -q
```

Critical assertions:

- callback_data <= 64 bytes;
- technical OSM titles are hidden;
- service/bank/police/etc do not pass quality filter;
- low/stale/conflict hours do not pass open-now reliability;
- renderers do not show debug/source/confidence fields;
- route with fewer than two valid points is unavailable;
- route/place cards include external map actions;
- admin bot analytics returns route funnel and no-result search data.

## Known Boundaries

- No full map inside Telegram.
- No route geometry drawing inside Telegram.
- No Redis in MVP; sessions are persisted in PostgreSQL.
- No broadcast/mass notification flow.
- Webhook exists, but docker-compose bot service currently runs polling.
