# Route Generation Diagnostics

## Таблицы

### route_generation_runs
- `city_id`, `user_id`, `request_json`
- `status`: `success` | `failed`
- `failure_reason`, `algorithm_version`
- `total_candidates`, `eligible_candidates`, `selected_places`
- `created_at`

### route_generation_candidates
- `generation_run_id`, `place_id`
- `is_eligible`, `score`, `selected`
- `rejection_reasons` (json array)
- `selection_reasons` (json array)

Миграция: `b2c3d4e5f6a8_add_route_generation_diagnostics.py`

## Когда пишется

| Источник | Функция |
|----------|---------|
| Canonical build | `record_canonical_generation` в `route_builder_flow` |
| `/routes/generate` | `record_itinerary_generation` |
| Admin dry-run | через canonical build + `generation_run_id` в ответе |

Ошибки записи diagnostics **не ломают** генерацию (try/except в record layer).

## Admin dry-run

`POST /admin/routes/dry-run` (auth: admin Bearer)

Параметры: `city_slug`, `duration_min`, `route_mode`, `interests`, `budget_level`, `start_lat/lng`, `limit`.

Ответ: `generation_run_id`, `selected_places`, `rejected_candidates`, counts.

Не создаёт пользовательский маршрут.

## Логи и события

**system_logs** (errors):
- `route_generation_failed`, `no_eligible_candidates`, и др. через `route_generation_logging`

**product_events**:
- `route_generation_started` / `success` / `failed`
- `admin_route_dry_run_success` / `failed`

## Retention (документировано, job позже)

- Prod runs: 90 дней
- Dry-run: 30 дней
- Очистка: `DELETE FROM route_generation_runs WHERE created_at < ...` (cascade candidates)

## Просмотр диагностики

1. Admin dry-run response — immediate rejected/selected
2. SQL: `route_generation_runs` + join `route_generation_candidates`
3. Pipeline trace в ответе canonical (при `X-Debug`) — stage counts, не per-place
