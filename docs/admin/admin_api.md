# Admin API (текущая фаза)

Все endpoint'ы требуют `Authorization: Bearer <ADMIN_API_TOKEN>`.

## Обзор и метрики

| Method | Path | Описание |
|--------|------|----------|
| GET | `/admin/overview` | Actionable cards |
| GET | `/admin/metrics/summary` | Метрики + product_events |
| GET | `/admin/coverage/summary` | Покрытие по городам |

## Места

| Method | Path | Описание |
|--------|------|----------|
| GET | `/admin/places` | Список + фильтры/preset |
| GET | `/admin/places/{id}/detail` | Карточка места |
| PATCH | `/admin/places/{id}` | Обновление полей |
| POST | `/admin/places/create-draft` | Создание draft |
| POST | `/admin/places/check-duplicates` | Проверка дублей |
| POST | `/admin/places/bulk/preview` | Preview массового действия |
| POST | `/admin/places/bulk/apply` | Применение (confirm=true) |
| POST | `/admin/places/address-refresh` | Обновление адресов |

## Города

| Method | Path | Описание |
|--------|------|----------|
| GET | `/admin/cities` | Список |
| GET | `/admin/cities/by-slug/{city_slug}/workspace` | Единый workspace города: карточка, readiness, import job, coverage |
| GET | `/admin/cities/{slug}/settings` | Inline feature toggles |
| PUT | `/admin/cities/{slug}/settings/{key}` | Изменить toggle |

## Таксономия

| Method | Path | Описание |
|--------|------|----------|
| GET | `/admin/taxonomy/categories` | Backend-driven список категорий для admin UI: справочник + реально встреченные категории |

## Маршруты (operations)

| Method | Path | Описание |
|--------|------|----------|
| GET | `/admin/routes/eligibility` | Eligibility dashboard: place pool, reasons, quality |
| GET | `/admin/routes/data-quality/{city_slug}` | Data quality отчёт по городу |
| GET | `/admin/routes/readiness` | Readiness score всех городов |
| GET | `/admin/routes/readiness/{city_slug}` | Readiness score одного города |
| POST | `/admin/routes/dry-run` | Dry-run генерации: selected/rejected candidates, `generation_run_id` |

Тело запроса: `city_slug`, `duration_min`, `route_mode`, `interests[]`, `budget_level`, `start_lat`, `start_lng`, `limit`.

Не создаёт пользовательский маршрут. Сохраняет `route_generation_runs` + `route_generation_candidates`.

См. `docs/routes/route_generation_diagnostics.md`.

## Логи

| Method | Path | Описание |
|--------|------|----------|
| GET | `/admin/audit-log` | Действия админов |
| GET | `/admin/system-logs` | Системные ошибки/события |

## Feature toggles

См. `docs/admin/feature_toggles.md`.
