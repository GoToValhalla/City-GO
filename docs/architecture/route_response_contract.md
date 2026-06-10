# Route Response Contract

## Эндпоинты

| Эндпоинт | Схема ответа | Схема точки |
|----------|-------------|------------|
| `POST /recommendations/route` | `RecommendationRouteResponse` | `RecommendationRoutePointResponse` |
| `POST /user-routes/build` | `UserRouteState` | `UserRoutePoint` |
| `POST /user-routes/correct` | `UserRouteState` | `UserRoutePoint` |
| `POST /user-routes/edit` | `UserRouteState` | `UserRoutePoint` |

## Поля точки маршрута

### Основные поля (существовали ранее)

| Поле | Тип | Описание |
|------|-----|----------|
| `place_id` | `str` | ID места |
| `title` | `str \| null` | Название |
| `address` | `str \| null` | Сырой адрес из БД |
| `lat` | `float` | Широта |
| `lng` | `float` | Долгота |
| `category` | `str` | Категория |
| `visit_minutes` | `int` | Время визита |
| `estimated_walk_minutes` | `int \| null` | Время пешком ДО этой точки |
| `estimated_arrival_time` | `str \| null` | ISO 8601 время прибытия |
| `estimated_departure_time` | `str \| null` | ISO 8601 время отправления |
| `time_status` | `str \| null` | Статус времени |
| `time_warning` | `str \| null` | Предупреждение о времени |
| `scoring_breakdown` | `dict` | Breakdown скоринга |

### Навигационные поля (добавлены в Route Navigation Layer)

| Поле | Тип | Описание |
|------|-----|----------|
| `display_location` | `str` | Адрес или `"Координаты: {lat}, {lng}"` |
| `has_address` | `bool` | `true` если адрес реальный |
| `navigation_url_google` | `str` | Google Maps URL |
| `navigation_url_yandex` | `str` | Яндекс Карты URL |
| `navigation_url_osm` | `str` | OpenStreetMap URL |
| `estimated_distance_meters` | `int \| null` | Дистанция до точки в метрах (haversine) |

## Метрики маршрута (верхний уровень)

| Поле | Тип | Описание |
|------|-----|----------|
| `total_walk_distance_meters` | `int` | Суммарная дистанция пешком |
| `total_estimated_minutes` | `int` | Суммарное время с учётом переходов |
| `estimated_distance` | `float` | Дистанция маршрута в км |
| `quality_score` | `float` | Качество данных (0-1) |

## Важные инварианты

1. Каждая точка маршрута гарантированно имеет `lat` и `lng` (иначе не попадает в маршрут).
2. Все три `navigation_url_*` всегда присутствуют если точка в маршруте.
3. `display_location` никогда не null для точек маршрута.
4. `estimated_distance_meters` — haversine, не turn-by-turn.
