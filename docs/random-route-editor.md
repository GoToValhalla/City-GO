# Random Route + Draft Editor MVP

Дата актуализации: 2026-06-22.

## Product Behavior

Random Route строит черновик пешего маршрута по route-eligible POI города. Черновик можно редактировать без пересборки всего маршрута:

- удалить точку;
- добавить точку;
- заменить точку;
- искать кандидатов по названию, адресу или category intent (`кофе` → `cafe`).

Если eligible places есть, backend не должен молча возвращать пустой маршрут. При нехватке точек возвращается `partial` route и typed warning.

## Category Modes

MVP поддерживает только:

- `none` — категории пользователя не применяются;
- `balanced` — выбранные категории дают scoring boost, но не фильтруют pool.

`focused` и `strict` не реализованы. Выбор `museum` в городе без музеев не должен обнулять маршрут, если есть другие eligible места.

## API

Основные endpoints:

```text
POST /routes/random
GET /routes/drafts/{id}
POST /routes/drafts/{id}/remove-point
POST /routes/drafts/{id}/add-point
POST /routes/drafts/{id}/replace-point
GET /routes/drafts/{id}/search-places
GET /cities/{slug}/start-points
POST /geo/resolve-start
POST /geo/resolve-address
```

Draft mutations требуют `version`. При stale version backend возвращает typed error `STALE_DRAFT_VERSION`.

## Fallback Rules

- `NO_ELIGIBLE_PLACES` — в городе нет опубликованных visible route-eligible мест с координатами.
- `RANDOM_FALLBACK_USED` — маршрут собран частично из лучших доступных мест.
- `OVER_BUDGET` — ручное добавление вывело маршрут за time budget, но операция не блокируется.
- `GEO_OUT_OF_CITY_FALLBACK` — геолокация далеко от центра города, старт заменён на city center.
- `ADDRESS_FALLBACK_CITY_CENTER` — address/query не найден, используется city center.

## Start Resolution

MVP не использует обязательный внешний geocoder. Start resolver ищет:

1. city center;
2. `city_start_points`;
3. published places by title/address fuzzy match;
4. fallback to city center.

Migration создаёт start point `Центр города` для городов с `center_lat/center_lng`.

## Frontend

MVP editor встроен на `/routes/generate` отдельным блоком `Random Route MVP`, чтобы не ломать существующий recommendation preview flow.

## Verification

```bash
DATABASE_URL=sqlite:///./ci_random_route_tests.db ADMIN_API_TOKEN=ci-admin-token APP_ENV=test \
  .venv/bin/python -m pytest --no-cov tests/test_random_route_drafts_api_new.py -q

npm run test -- RandomRouteDraftEditor.test.tsx
npm run lint
npm run build
```
