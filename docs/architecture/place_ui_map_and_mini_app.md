# Place UI, Map and Telegram Mini App

## Implemented user UI

The places screen now uses the City GO Place UI components and a linked map/list layout.

Key files:

- `frontend/src/pages/places/PlacesListPage.tsx` - places screen with search, filters, linked map and list.
- `frontend/src/components/places/PlaceMapPanel.tsx` - embedded map panel, active place state, bottom place card and geolocation action.
- `frontend/src/components/places/PlaceList.tsx` - list states and active place propagation to the map.
- `frontend/src/components/places/PlaceCard.tsx` - place card that can activate the map on focus/hover and still opens Place Detail on click.
- `frontend/src/components/places/PlaceMapBottomCard.tsx` - compact map overlay card for the selected place.
- `frontend/src/shared/map/yandexMaps.ts` - Yandex widget/external map URL helpers.
- `frontend/src/shared/location/useUserLocation.ts` - browser geolocation wrapper with Russian inline errors.
- `frontend/src/styles/place-map.css` - responsive map/list layout and Telegram-safe bottom overlay styles.

## Map provider

Current implementation uses Yandex Maps iframe widgets instead of a custom map SDK. This is intentional for now:

- no extra frontend dependency;
- works inside WebView/Telegram when the frontend is served over HTTPS;
- legal use is limited to map display and outbound map opening, not copying Yandex place data into City GO storage;
- the map is linked with the list through active place state and marker URL regeneration.

The current iframe approach does not give full SDK-level marker click events. `PlaceMapPanel` therefore provides a small in-app pin selector and list-card activation. If full marker click control is required, the next implementation should switch `PlaceMapPanel` internals to Yandex Maps JS API or 2GIS MapGL while keeping the same component props.

## Geolocation

`useUserLocation` uses `navigator.geolocation.getCurrentPosition`.

Platform requirements:

- works on `https://` origins;
- works on `localhost` for development;
- does not work on a plain public IP over `http://`;
- in Telegram Mini App it is still a WebView browser permission flow, so HTTPS is required.

When geolocation is blocked or unavailable, the UI shows an inline Russian error. It does not use `alert` or modal errors.

## Telegram Mini App

Implemented files:

- `frontend/index.html` includes `https://telegram.org/js/telegram-web-app.js`, Russian document language, `viewport-fit=cover` and dark theme color.
- `frontend/src/shared/telegram/useTelegramMiniApp.ts` initializes Telegram WebApp with `ready`, `expand`, dark header/background colors and hides the MainButton.
- `frontend/src/pages/telegram/TelegramMapPage.tsx` uses the Telegram hook and shared Yandex map helpers.
- `telegram_bot/keyboards/main_menu.py` adds the `🌐 Открыть City GO` WebApp button when `TELEGRAM_MINI_APP_URL` is configured with an HTTPS URL.

Important deployment rule:

Telegram WebApp buttons require HTTPS. If `TELEGRAM_MINI_APP_URL` is empty or starts with `http://`, the bot does not create a WebApp button. For a temporary IP-only backend/frontend, use a temporary HTTPS tunnel or deployment URL and set:

```env
TELEGRAM_MINI_APP_URL=https://<public-https-host>
```

## Backend data needed by map/list UI

The frontend `Place` type now includes optional `lat` and `lng`, matching the backend `PlaceRead` schema. Places without coordinates are still listed, but are skipped by the embedded map.

## Remaining route-map work

Route UI still needs its own route map component with ordered waypoints, active step, route polyline and live route actions. Reuse the map helper/component contract from `PlaceMapPanel`, but do not couple route state to the places list implementation.
