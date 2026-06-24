# Location and Map Platform

## Boundaries

Location state is owned by `frontend/src/shared/location`. Screens never call
`navigator.geolocation` or Telegram APIs directly. The public contract exposes
one-shot `request`, browser-only `startWatch`/`stopWatch`, manual selection,
city-center fallback and explicit `clear`.

Provider priority:

1. Telegram Mini App `LocationManager`;
2. Browser Geolocation;
3. Telegram Bot shared coordinates;
4. Manual map point;
5. Selected city center.

No provider is invoked during page load. A user action is required.

## State Contract

Every result has a Russian user message and one of:
`idle`, `initializing`, `requesting`, `granted`, `denied`, `unavailable`,
`timeout`, `insecure`, `error`.

Coordinates include accuracy, optional altitude/course/speed, source,
capture time, stale flag, permission state and retryability. Exact coordinates
live in memory and session storage only until `VITE_LOCATION_TTL_SECONDS`.

## Telegram

Telegram `LocationManager` is initialized before use and treated as a one-shot
provider. `openSettings` is exposed only to a button handler. Viewport and
safe-area events only trigger layout updates. Browser geolocation remains the
fallback for unsupported Telegram versions and Desktop clients without native
location support.

## Browser

One-shot requests use `getCurrentPosition`. Active navigation alone may use
`watchPosition`. The watcher is cleared on stop, completion, route change and
unmount. Insecure HTTP origins never call the browser API.

## Map

`MapLibreMap` accepts provider-neutral points, route geometry and user
location. It owns the MapLibre instance, sources, layers, listeners and cleanup.
The configured style is `VITE_MAP_STYLE_URL`; otherwise a raster style is built
from `VITE_MAP_TILE_URL`. A WebGL or tile failure leaves the list usable.

Markers and clusters use GeoJSON sources. Selection is bidirectional:
card selection centers the map; marker selection activates and scrolls the
card. Places without coordinates remain in the list and are excluded from map
bounds.

## Privacy

Exact coordinates are excluded from analytics and ordinary logs. Allowed
analytics fields are provider, permission outcome, scenario and coarse accuracy
bucket. Telegram Bot coordinates and pending intents expire; expired state is
removed before use. City-center fallback never masquerades as device location.

## Failure Policy

Every location failure offers at least one valid next action: retry, Telegram
settings, manual map selection or selected city center. Missing map credentials,
WebGL or tiles never block place lists or route controls.
