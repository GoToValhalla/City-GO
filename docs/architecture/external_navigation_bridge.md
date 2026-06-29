# External Navigation Bridge

## Назначение

External Navigation Bridge — временный production-слой между City GO route engine и внешними картами. City GO остаётся источником истины по маршруту: выбирает места, порядок, длительность, карточки, прогресс и аналитику. Яндекс Карты и 2ГИС используются только как внешний навигационный экран.

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
  "providers": ["yandex_maps", "2gis"],
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

Для 2ГИС координаты передаются в порядке `longitude,latitude`. Для Яндекс web route links — в порядке `latitude,longitude` внутри `rtext`.

### Full route

Full route включается только для коротких маршрутов. Сейчас он доступен только как preview в Яндекс Картах, потому что внешний provider может изменить порядок точек. Если точек больше безопасного лимита или URL слишком длинный, full route отключается, а segment mode остаётся рабочим.

## Frontend / TMA behavior

На route detail page есть route player:

- `Начать маршрут`;
- текущая точка;
- кнопки внешней навигации;
- `Я на месте`;
- `Следующая`;
- `Завершить`;
- localStorage persistence для браузера, мобильного браузера и Telegram Mini App.

Для Telegram Mini App используется `Telegram.WebApp.openLink`, если он доступен. Для обычного браузера используется новое окно/вкладка.

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

Админ-аналитика агрегирует открытия, fallback, возвраты, подтверждения точек и provider breakdown.

## Admin

В админке External Navigation Bridge должен быть понятен через:

- метрики в `/admin/analytics`;
- event breakdown по navigation events;
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

- Не парсить ответы Яндекс/2ГИС API без отдельного лицензионного решения.
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
- плохие координаты не ломают response;
- full route отключается для длинных маршрутов.

Frontend/TMA:

- кнопки видны на desktop browser;
- кнопки видны на mobile browser;
- Telegram Mini App открывает ссылку через `openLink`;
- localStorage не сбрасывает прогресс;
- route player остаётся рабочим без внешней карты.

Admin:

- navigation events видны в breakdown;
- provider metrics агрегируются;
- `navigation_ready_pct` помогает найти маршруты без координат.
