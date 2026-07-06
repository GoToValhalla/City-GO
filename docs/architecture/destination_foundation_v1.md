# Destination-first foundation v1

Текущая реализация (фаза v1): параллельная модель `Destination` поверх legacy `City` без big-bang миграции.

## Модели

| Таблица | Файл | Назначение |
|---------|------|------------|
| `destinations` | `models/destination.py` | User-facing туристическая сущность |
| `destination_scopes` | `models/destination.py` | Географический/import/route контур |
| `destination_place_memberships` | `models/destination.py` | Принадлежность Place → Destination |
| `destination_membership_conflicts` | `models/destination.py` | Конфликты пересекающихся scope |
| `places.primary_destination_id` | `models/place.py` | Основное направление места |
| `places.destination_assignment_stale` | `models/place.py` | Флаг для пересчёта membership |

`City` и `places.city_id` (NOT NULL) сохранены. Каждый город backfill'ится в `Destination` с `legacy_city_id`.

Миграция: `migrations/versions/f7a8b9c0d1e2_destination_foundation_v1.py`.

## Feature flags (`core/config.py`)

| Флаг | Default | Поведение |
|------|---------|-----------|
| `DESTINATION_FOUNDATION_ENABLED` | `false` | Мастер-флаг foundation |
| `DESTINATION_CATALOG_READS_ENABLED` | `false` | Каталог мест через membership JOIN |
| `DESTINATION_ROUTE_READS_ENABLED` | `false` | Кандидаты маршрута через membership |
| `DESTINATION_IMPORT_ENABLED` | `false` | Shadow-write membership при импорте |

Хелперы: `services/destination_flags.py`.

## Compatibility layer

`services/city_destination_compatibility.py`:

- `city_id` / `city_slug` → `destination_id` через `legacy_city_id`
- fallback на `City`, если Destination не найден
- старые payload `/places?city_slug=` и `/v1/user-routes/build` не ломаются

## Сервисы

| Модуль | Ответственность |
|--------|-----------------|
| `destination_service.py` | list/get/create destinations |
| `destination_membership_service.py` | upsert/hide/stale memberships |
| `destination_backfill_service.py` | idempotent cities → destinations |
| `destination_membership_recalculation_service.py` | bbox-based recalc, conflicts |
| `destination_places_query.py` | catalog JOIN без ST_Contains |
| `destination_route_guard.py` | walking guard для region/remote |
| `destination_route_resolution.py` | resolve build request |
| `destination_data_pipeline_service.py` | destination-owned pipeline orchestration |
| `destination_import_service.py` | bbox scope candidate import and membership upsert |
| `destination_enrichment_pipeline.py` | deterministic enrichment through MergeService |
| `destination_readiness_service.py` | admin readiness metrics |

## Public API

- `GET /v1/destinations` — опубликованные направления
- `GET /v1/destinations/{slug}` — детали + children + scopes
- `GET /places?destination_slug=` — каталог по membership (при флаге) или legacy city compat
- `GET /places?city_slug=` — без изменений
- Оба slug → `400`
- `POST /v1/user-routes/build` — опционально `destination_id`/`destination_slug`, `trip_type`

## Route Engine (точечные изменения)

`services/candidate_retrieval_service.py`: при `DESTINATION_ROUTE_READS_ENABLED` + destination в context — JOIN `destination_place_memberships`, exclude `is_hidden`.

Walking guard: region/natural без `is_walkable_cluster` → `422 walking_not_supported_for_destination`.

## Admin API

Префикс `/admin/destinations`:

- list/create/detail
- scopes list/create
- memberships list
- assign-place / hide-place
- orphans/places
- conflicts/list
- data-pipeline run/latest/history/details/stop
- memberships/recalculate
- readiness
- review-items
- geo-search / from-geo-candidate / scopes/from-geo-candidate (геокандидат из Nominatim; snapshot передаётся клиентом в POST)
- `/admin/discovery` — region-first discovery: search → preview job → bulk create

UI: `AdminDiscoveryPage` (основной поток), `AdminDestinationsPage` (список), `AdminDestinationDetailPage`, `AdminDestinationGeoSearchPanel` (fallback: поиск города и ручные контуры; recover только по явному включению).

## Backfill

`backfill_cities_to_destinations(db)` — idempotent:

1. City → Destination (`destination_type=city`)
2. default scope из bbox/center
3. Place → membership (`assignment_type=legacy_city`, `is_primary=true`)

## Ограничения v1

- Геометрия: bbox JSON, без PostGIS на hot path
- `places.city_id` обязателен при записи
- Import по `destination_slug` — shadow write в `create_place`; полный scope-import реализован в Destination Data Pipeline v1 через bbox JSON adapter
- Production rollout: включать флаги поэтапно

См. также: [`destination_data_pipeline_v1.md`](destination_data_pipeline_v1.md).

## Тесты

`tests/test_destination_foundation_v1_new.py` — backfill, catalog, route candidates, walking guard, admin, conflicts, service_only.

## Production smoke (после деплоя)

1. `GET /health`
2. `GET /v1/destinations`
3. `GET /places?city_slug=zelenogradsk`
4. `GET /places?destination_slug=zelenogradsk` (после включения catalog flag)
5. `POST /v1/user-routes/build` с city payload
6. Admin `/admin/destinations`
