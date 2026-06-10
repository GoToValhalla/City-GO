# Админка City Go — переработка (текущая фаза)

## Новая структура разделов (RU)

| Маршрут | Раздел |
|---------|--------|
| `/admin/overview` | Обзор (actionable cards) |
| `/admin/cities` | Города |
| `/admin/places` | Места |
| `/admin/coverage` | Покрытие данных |
| `/admin/photos` | Фото |
| `/admin/verification` | Верификация |
| `/admin/imports` | Импорты |
| `/admin/enrichment` | Обогащение данных |
| `/admin/features` | Фичи и настройки |
| `/admin/metrics` | Метрики |
| `/admin/audit` | Журнал аудита |

Старые URL (`/admin/dashboard`, `/place-images`, …) редиректят на новые.

## Backend (добавлено)

- `GET /admin/overview` — карточки «что требует внимания»
- `GET /admin/metrics/summary` — сводные метрики (DAU/MAU — заглушки до event pipeline)
- `GET/PUT /admin/feature-toggles` — глобальные и city-scope toggles (таблица `feature_toggles`)
- `GET /admin/place-verifications/summary` — сводка очереди без обязательного `city_slug`
- `GET /admin/place-verifications/stats` — `city_slug` опционален (default из БД)
- `GET /admin/coverage/summary` — покрытие и quality score по всем городам
- `GET /admin/places` — расширенные фильтры: `preset`, `has_photo`, `has_address`, `category`, `route_eligible`, …
- `GET /admin/audit-log` — фильтры `action`, `actor`, `entity_id`
- Feature toggles влияют на: список городов, maintenance mode, AI, верификацию, модерацию фото, маршруты, фильтры качества мест по городу
- Миграции: `e8f1a2b3c4d5` (таблица), `f9a2b3c4d5e6` (seed defaults). На prod применяются автоматически через `docker compose up migrate` в deploy workflow

## Feature toggles

Хранятся в `feature_toggles`, изменения пишутся в `admin_audit_logs`.
Глобальные ключи — `services/feature_toggle_defs.py`.
City keys — `CITY_TOGGLE_KEYS` (подключение к route/visibility — поэтапно).

## Mobile

`AdminResponsive.css`: burger menu, drawer sidebar, vertical filters, table horizontal scroll.

## Проверка

```bash
pytest tests/test_admin_ops_new.py -q
cd frontend && npm run build && npm run test -- --run adminErrorMessage_new
```

Требуется `ADMIN_API_TOKEN` / `VITE_ADMIN_API_TOKEN` для доступа к API.

## Добавлено (операционная фаза)

- Карточка места: `/admin/places/{id}`
- Создание места: `/admin/places/new` → draft flow
- Массовые действия: preview + apply
- Inline city settings в `/admin/cities`
- Системные логи: `/admin/system-logs`
- Product events + расширенные метрики
- Миграция `a1b2c3d4e5f7`: system_logs, product_events, admin_operations, поля адреса места

См. также: `docs/admin/admin_api.md`, `docs/admin/feature_toggles.md`, `docs/admin/prod_smoke_checklist.md`

## Известные ограничения

- DAU/MAU — заглушки до auth events
- Route usage — счётчик по RoutePlace, не динамические построения
- Address scheduler по расписанию — только ручной/bulk action + документированный follow-up
- City quality toggles — технический долг (см. feature_toggles.md)
- Следующий этап: маршруты (route debug, live editing guards)
