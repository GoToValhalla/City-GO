# Telegram Product UI

City GO has two Telegram surfaces and they must not be mixed up:

- Telegram bot: compact chat messages, callbacks and inline buttons from `telegram_bot/`.
- Telegram Mini App: the React frontend opened inside Telegram through `web_app` buttons.

The screenshots from Telegram chat are the bot surface, not the Mini App. A regular bot message cannot embed an interactive map inside the chat bubble. Maps and full place UI are opened through the Mini App/WebView.

## Updated files

- `telegram_bot/renderers.py`: Telegram message cards for start, city selection, main menu, routes, route steps, places, nearby, open-now, search, help and errors.
- `telegram_bot/keyboards/catalog.py`: inline keyboards for menu, routes, route mode, places, favorites, location fallback and pagination. If `TELEGRAM_MINI_APP_URL` is set to a public HTTPS frontend URL, map/detail buttons use Telegram `web_app`; otherwise they fall back to normal map URLs.
- `telegram_bot/schemas.py`: bot-facing place and route schemas include `slug` for Mini App deep links.
- `telegram_bot/services/facade.py`: passes place and route slugs from database rows into bot UI schemas.
- `frontend/src/pages/telegram/TelegramMapPage.tsx`: Mini App map screen for a selected point.
- `frontend/src/styles/telegram-mini-app.css`: dark Telegram-native styling and safe-area handling for Mini App map screen.
- `frontend/src/App.tsx`: registers `/telegram/map`.
- `.env.example` and `core/config.py`: document and expose `TELEGRAM_MINI_APP_URL`.

## Mini App configuration

Set `TELEGRAM_MINI_APP_URL` to the public HTTPS frontend origin, for example the production frontend URL without a trailing slash.

Expected behavior after deploy:

- `Открыть City GO` opens the frontend inside Telegram;
- place detail buttons open `/places/{slug}` inside Telegram when slug exists;
- route buttons open `/routes/{slug}` inside Telegram when slug exists;
- map buttons open `/telegram/map?lat=...&lng=...` inside Telegram;
- if the Mini App URL is empty or not HTTPS, buttons fall back to normal Yandex Maps links.

## Message rules

Telegram messages should stay compact:

- place cards show title, localized category, status/hours, address only when available, and distance only when available;
- route cards show route meta and ordered points, not long prose;
- route mode shows progress, current point, visited/skipped counts and distance when Telegram location is known;
- empty states are honest and short;
- error states are Russian and route the user back to the menu.

## Actions

Telegram action labels follow the same intent as the web UI:

- `Начать` for route start;
- `Точки по порядку` for route order;
- `На карте` for point map;
- `Открыть маршрут` for route Mini App view;
- `Подробнее в City GO` for place Mini App view;
- `Сохранить` / `Убрать` for favorites;
- `Похожие` for category replacement/discovery;
- `Я на месте`, `Пропустить`, `Предыдущая`, `Следующая`, `Завершить` for route mode.

## Null and fallback handling

- no reliable hours: show `Уточнить часы`;
- no place photo or Telegram photo send failure: fall back to text card;
- unknown category: show `Место`, not raw backend key;
- long titles in buttons: clean and clamp before rendering;
- no city: show a public empty state, not admin instructions;
- no Mini App URL: use regular external map links.

## Manual checks after deploy

Run these through the real bot or webhook sandbox:

- `/start` with no selected city;
- city selection with one and multiple public cities;
- main menu buttons;
- `Открыть City GO` opens inside Telegram when `TELEGRAM_MINI_APP_URL` is configured;
- route list, route card, route mode, visit/skip/finish;
- route detail opens inside Mini App for saved routes with slug;
- place category list, place card with and without photo;
- place detail opens inside Mini App for places with slug;
- point map opens inside Mini App through `/telegram/map`;
- fallback Yandex map URL works when Mini App URL is not configured;
- open-now empty and success states;
- nearby flow with Telegram location and without location;
- text search with results and no results;
- favorites add/remove.
