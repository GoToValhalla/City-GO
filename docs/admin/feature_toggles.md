# Feature toggles City Go

## Назначение

Feature toggles включают/выключают **функциональность** (rollout, maintenance, AI layer, route engine).

## Не использовать для контентной логики

Следующее — **бизнес-данные в моделях**, не toggles:

| Настройка | Поле модели |
|-----------|-------------|
| Место опубликовано | `Place.publication_status`, `is_published` |
| Видимость пользователям | `Place.is_visible_in_catalog` |
| Участие в маршрутах | `Place.is_route_eligible` |
| Категория / теги | `Place.category`, `PlaceTag` |
| Статус города | `City.launch_status`, `City.is_active` |

City-level toggles (`hide_without_photo`, `verified_places_only`) — **фильтры видимости на уровне города**, не замена полей места. Технический долг: часть качества места дублируется toggles + поля Place — план переноса в `CitySettings` JSON.

## API

- `GET /admin/feature-toggles?scope=global|city&city_slug=...`
- `PUT /admin/feature-toggles/{key}?scope=...`
- `GET /admin/feature-toggles/groups`
- Inline города: `GET/PUT /admin/cities/{slug}/settings/{key}`

## Где влияют

См. `services/feature_toggle_guards.py`, `core/public_access_middleware.py`, `services/city_place_filters.py`.
