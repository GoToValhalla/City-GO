# Route Builder v2 Production Integration

Jira: CITYGO-159

## Цель

Route Builder v2 должен проходить через реальный пользовательский путь, а не оставаться только контрактным сервисом.

Целевая цепочка:

```text
published/catalog-visible/route-eligible places
→ public route candidate retrieval
→ Route Builder v2 plan
→ existing route engine
→ /v1/user-routes/build
→ frontend route screen
→ production smoke by flag
```

## Что подключено

### 1. API integration

`/v1/user-routes/build` теперь проходит через `UserRouteBuildService`, который перед запуском legacy route engine строит `RouteBuilderV2Plan`.

Источник payload:

- `build_mode=auto` → `quick`
- `build_mode=by_categories` → `category`
- `build_mode=manual` → `manual`
- `build_mode=constructor` → `slot`

Ошибки контракта Route Builder v2 возвращаются как HTTP 422 с кодом `route_builder_v2_invalid_request`.

### 2. Data gates

Route Builder v2 post-build gate удаляет utility/junk точки из результата:

- pharmacy / apteka
- bus_stop / stop / transport
- service / utility
- atm / bank
- parking / toilet / fuel / bench / shop / supermarket / mall

Если после удаления остаётся меньше точек, чем требует режим, маршрут становится:

- `partial_route`, если осталась хотя бы одна точка;
- `no_route`, если точек не осталось.

`partial_reason`: `route_builder_v2_insufficient_points`.

### 3. Public data contract

Route Builder v2 не создаёт отдельный read path. Он использует существующий production retrieval path, где кандидаты берутся через public/catalog-visible/route-eligible условия.

В `debug_trace` добавляется stage:

```json
{
  "stage": "route_builder_v2",
  "data_contract": "public_catalog_visible_route_eligible_only"
}
```

### 4. Frontend smoke contract

Frontend route form теперь явно отправляет Route Builder v2-compatible поля:

- `build_mode`
- `selected_place_ids`
- `route_slots`

Если пользователь выбрал интересы, frontend отправляет `build_mode=by_categories`. Если интересы пустые, отправляет `build_mode=auto`.

### 5. Production smoke

Production smoke уже содержит route check behind flag:

- `CITY_GO_ROUTE_SMOKE_ENABLED=true`
- `CITY_GO_ROUTE_SMOKE_CITY_ID=<stable city slug/id>`
- `CITY_GO_ROUTE_SMOKE_LAT=<lat>`
- `CITY_GO_ROUTE_SMOKE_LNG=<lng>`

Пока флаг выключен по умолчанию, чтобы unstable city data не ломала deploy smoke.

## Tests

Backend:

- Route Builder v2 plan from real user route payload.
- Quick mode from `auto` payload.
- Output gate removes junk points.
- Output gate marks partial route when too few points remain.
- API contract returns 422 for invalid manual payload.

Frontend:

- Route form sends Route Builder v2 fields.
- Interest route uses `by_categories`.
- Empty-interest route uses `auto`.

## Что проверять после CI

1. `/v1/user-routes/build` работает с `build_mode=auto`.
2. `/v1/user-routes/build` работает с `build_mode=by_categories`.
3. При invalid manual payload API возвращает 422, а не 500.
4. В route response появляется `debug_trace.stage=route_builder_v2`.
5. В route response не остаются pharmacy/bus_stop/utility точки.
6. Frontend `/routes/generate` не падает и отправляет Route Builder v2-compatible payload.

## Ограничения текущей итерации

Manual/constructor modes подключены на уровне API contract и v2 plan. Их full UX ещё требует отдельного TMA/UI конструктора с выбором конкретных places/slots и сохранением route session.

Production route smoke остаётся выключенным флагом до выбора стабильного города/dataset.
