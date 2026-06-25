# Route Navigation Layer

## Цель

Каждая точка маршрута должна быть пригодна для навигации, а линия на карте должна показывать реальный пешеходный путь по улицам и проходам, а не прямые отрезки между координатами.

## Пешеходная геометрия

Frontend отправляет упорядоченные координаты в:

```http
POST /routes/walking-geometry
```

Backend `services/walking_route_service.py` запрашивает OSRM-compatible pedestrian router и возвращает:

- GeoJSON geometry в порядке `[longitude, latitude]`;
- общую дистанцию и длительность;
- переходы между остановками;
- русские пошаговые инструкции;
- статус `routed` или `unavailable`.

Настройки:

```env
WALKING_ROUTER_URL=https://routing.openstreetmap.de/routed-foot/route/v1/driving
WALKING_ROUTER_TIMEOUT_SECONDS=12
WALKING_ROUTER_USER_AGENT=CityGoWalkingRouter/1.0
```

Провайдер можно заменить собственным OSRM foot instance без изменения frontend. Запросы одинаковых наборов координат кэшируются в процессе backend.

### Безопасная деградация

Если pedestrian router недоступен, карта показывает маркеры, но не рисует прямую линию. Это обязательное правило: ложная линия через здания, воду или закрытую территорию опаснее отсутствующей линии.

## Как пользователь понимает, куда идти

1. На карте показан путь по пешеходному графу.
2. Под картой отображаются фактическая дистанция и время.
3. Блок «Как пройти» разбит по переходам между точками и содержит манёвры.
4. Нажатие на маркер показывает выбранную остановку.
5. При недоступности routing API пользователь видит понятное предупреждение без ложного маршрута.

## Навигационные поля в route response

Каждая точка маршрута (`UserRoutePoint`, `RecommendationRoutePointResponse`) содержит:

| Поле | Тип | Описание |
|------|-----|----------|
| `display_location` | `string` | Адрес или `Адрес уточняется · открыть на карте` |
| `has_address` | `bool` | Есть ли подтверждённый адрес |
| `navigation_url_google` | `string` | Google Maps URL |
| `navigation_url_yandex` | `string` | Яндекс Карты URL |
| `navigation_url_osm` | `string` | OpenStreetMap URL |
| `estimated_distance_meters` | `int \| null` | Предварительная оценка до запроса routing API |
| `estimated_walk_minutes` | `int \| null` | Предварительная оценка времени перехода |

Предварительные метрики route engine используются для подбора точек. После построения карты пользовательские метрики берутся из pedestrian router.

## Fallback без адреса

```text
address пустой/плейсхолдер → display_location = Адрес уточняется · открыть на карте
                           → has_address = false
                           → navigation URLs используют lat/lng
```

## Debug lifecycle

Debug UI выключен по умолчанию и не должен включаться после деплоя.

- `VITE_DEBUG_PANEL=false` — production default.
- `?debug=1` — однократно включает debug и сохраняет выбор в localStorage.
- `?debug=0` — выключает debug.
- Кнопка «Выключить» полностью удаляет панель; плавающая кнопка не остаётся.
- Route debug trace отображается только при включённом debug.

## Telegram

Telegram-бот сохраняет ссылки на внешние карты для резервного открытия конкретной точки. Встроенная Web App карта использует тот же endpoint пешеходной геометрии.

## Следующие улучшения

- собственный OSRM/Valhalla instance для гарантированного SLA;
- перерасчёт порядка точек по матрице реальных walking distances;
- голосовые подсказки и отклонение от маршрута;
- режимы велосипед и общественный транспорт.
