# Telegram Product UI

City GO Telegram bot lives in `telegram_bot/` and uses the same product canon as the web/TMA UI: short cards, Russian labels, no admin/debug copy, no raw backend category keys, and clear actions.

## Updated files

- `telegram_bot/renderers.py`: Telegram message cards for start, city selection, main menu, routes, route steps, places, nearby, open-now, search, help and errors.
- `telegram_bot/keyboards/catalog.py`: inline keyboards for menu, routes, route mode, places, favorites, location fallback and pagination.

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
- `Маршрут` / `На карте` for map navigation;
- `Сохранить` / `Убрать` for favorites;
- `Похожие места` for category replacement/discovery;
- `Я на месте`, `Пропустить`, `Предыдущая`, `Следующая`, `Завершить` for route mode.

## Null and fallback handling

- no reliable hours: show `Уточнить часы`;
- no place photo or Telegram photo send failure: fall back to text card;
- unknown category: show `Место`, not raw backend key;
- long titles in buttons: clean and clamp before rendering;
- no city: show a public empty state, not admin instructions.

## Manual checks after deploy

Run these through the real bot or webhook sandbox:

- `/start` with no selected city;
- city selection with one and multiple public cities;
- main menu buttons;
- route list, route card, route mode, visit/skip/finish;
- place category list, place card with and without photo;
- open-now empty and success states;
- nearby flow with Telegram location and without location;
- text search with results and no results;
- favorites add/remove.
