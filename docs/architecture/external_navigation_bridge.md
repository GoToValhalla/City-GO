# External Navigation Bridge

## Назначение

External Navigation Bridge — временный production-слой между City GO route engine и внешними картами. City GO остаётся источником истины по маршруту: выбирает места, порядок, длительность, карточки, прогресс и аналитику. Яндекс Карты, 2ГИС и Google Maps используются только как внешний навигационный экран.

Этот слой специально отделён от route engine, чтобы будущая встроенная карта и навигация подключались без переписывания построения маршрутов.

## Архитектурный принцип

```text
Route Engine
  -> ordered waypoints
    -> ExternalNavigationService
      -> provider links
        -> Web / Mobile Web / Telegram Mini App
```

Route Engine не знает о provider URL, deeplink и особенностях Telegram. Он отдаёт упорядоченные точки. `ExternalNavigationService` превращает точки в независимый `navigation` block.

## Основной режим

Основной режим — `segment_first`.

Это означает:

- пользователь проходит маршрут внутри City GO;
- внешняя карта открывается для текущей точки или сегмента;
- порядок точек не делегируется внешней карте;
- full route во внешней карте является preview-only, не основным сценарием.

## API contract

Route detail responses содержат поле `navigation`:

```json
{
  "mode": "segment_first",
  "providers": ["yandex_maps", "2gis", "google_maps"],
  "navigation_ready_pct": 100.0,
  "destination_links": [],
  "segments": [],
  "full_route": {
    "available": true,
    "recommended": false,
    "reason": "preview_only_segment_navigation_is_primary",
    "links": []
  },
  "warnings": [],
  "future_internal_map_contract": "ordered_waypoints_and_segments"
}
```

### Destination links

Destination links открывают конкретную точку. Они нужны для первого шага маршрута и для пользователей, которые начинают не из предыдущей точки.

### Segment links

Segment links строятся для каждой пары `from -> to`.

Для 2ГИС координаты передаются в порядке `longitude,latitude`. Для Яндекс web route links — в порядке `latitude,longitude` внутри `rtext`. Для Google Maps используются публичные web URLs с `api=1`, `origin`, `destination` и `travelmode=walking`.

### Full route

Full route включается только для коротких маршрутов и является preview-only. City GO остаётся источником порядка точек, даже если внешний provider перестроит маршрут.

Google Maps full route добавляется только если промежуточных точек не больше безопасного mobile-лимита и URL остаётся коротким. Если Google full route недоступен, сегментная Google-навигация всё равно остаётся рабочей.

## Providers

### yandex_maps

- Destination: точка на Яндекс Картах.
- Segment: пеший `rtext=from~to`.
- Full route: preview-only для коротких маршрутов.

### 2gis

- Destination: точка в 2ГИС.
- Segment: `routeSearch/rsType/pedestrian/from/lon,lat/to/lon,lat`.
- Full route: не используется в MVP.

### google_maps

- Destination: `https://www.google.com/maps/search/?api=1&query={lat},{lng}`.
- Segment: `https://www.google.com/maps/dir/?api=1&origin={lat},{lng}&destination={lat},{lng}&travelmode=walking`.
- Full route: `origin`, `destination`, `waypoints`, `travelmode=walking`, preview-only.
- Не используется Google Maps JavaScript API, Google Routes API, Distance Matrix API и API key.

## Frontend / TMA behavior

На route detail page есть route player:

- `Начать маршрут`;
- текущая точка;
- кнопки внешней навигации;
- `Я на месте`;
- `Следующая`;
- `Завершить`;
- localStorage persistence для браузера, мобильного браузера и Telegram Mini App.

Для Telegram Mini App используется `Telegram.WebApp.openLink`, если он доступен. Для обычного браузера используется новое окно/вкладка. Google Maps открывается тем же механизмом, что Яндекс и 2ГИС.

## Analytics

События внешней навигации пишутся в `product_events` через endpoint `/navigation-events/`.

Основные события:

- `external_navigation_opened`;
- `external_navigation_fallback_used`;
- `external_navigation_returned`;
- `waypoint_confirmed`;
- `waypoint_skipped`;
- `route_completed`;
- `route_abandoned`.

Админ-аналитика агрегирует открытия, fallback, возвраты, подтверждения точек и provider breakdown. Google Maps отображается как provider `google_maps`.

## Admin

В админке External Navigation Bridge должен быть понятен через:

- метрики в `/admin/analytics`;
- event breakdown по navigation events;
- provider breakdown по `yandex_maps`, `2gis`, `google_maps`;
- `navigation_ready_pct` в route response для диагностики качества;
- предупреждения `some_points_have_no_valid_coordinates`, `not_enough_points_for_segment_navigation`, `too_many_points_for_stable_full_route`.

## Fallbacks

| Сценарий | Поведение |
|---|---|
| Приложение карты не установлено | Используется web URL |
| Точка без координат | Точка не попадает в navigation links, route response не ломается |
| Меньше 2 валидных точек | Segment links не строятся, отдаётся warning |
| Слишком короткий сегмент | Кнопки внешней карты скрываются для сегмента |
| Длинный маршрут | Full route отключается, segment mode остаётся |
| Google full route превышает mobile-лимит | Google full route не отдаётся, segment mode остаётся |
| Пользователь ушёл во внешнюю карту | City GO сохраняет состояние через route player/localStorage |
| Внешняя карта меняет порядок | Игнорируется; порядок City GO остаётся источником истины |

## Future embedded map

Когда появится встроенная карта, не надо менять route engine. Нужно заменить/расширить только navigation layer:

```text
ExternalNavigationBlock
  -> InternalMapNavigationBlock
     -> GeoJSON / polyline / provider SDK adapter
```

Сохранить нужно:

- ordered waypoints;
- segments;
- route session state;
- progress events;
- admin metrics;
- quality warnings.

## Что нельзя делать

- Не парсить ответы Яндекс/2ГИС/Google API без отдельного лицензионного решения.
- Не использовать Google Maps JavaScript API, Google Routes API или Distance Matrix API в этом bridge.
- Не считать внешний provider источником порядка точек.
- Не хранить прогресс только во внешней карте.
- Не включать background GPS tracking в MVP.
- Не блокировать прохождение маршрута, если внешняя карта не открылась.
- Не смешивать provider-specific URL logic с route engine.

## Test checklist

Backend:

- segment links строятся для `N-1` пар точек;
- 2ГИС получает `lon,lat`;
- Яндекс route URL получает `lat,lng`;
- Google destination URL использует `search/?api=1&query=`;
- Google segment URL использует `dir/?api=1`, `origin`, `destination`, `travelmode=walking`;
- Google full route использует `waypoints` только в безопасных пределах;
- плохие координаты не ломают response;
- full route отключается для длинных маршрутов.

Frontend/TMA:

- кнопки видны на desktop browser;
- кнопки видны на mobile browser;
- Telegram Mini App открывает ссылку через `openLink`;
- Google Maps отображается третьим provider;
- localStorage не сбрасывает прогресс;
- route player остаётся рабочим без внешней карты.

Admin:

- navigation events видны в breakdown;
- provider metrics агрегируются;
- `google_maps` виден в provider breakdown;
- `navigation_ready_pct` помогает найти маршруты без координат.
