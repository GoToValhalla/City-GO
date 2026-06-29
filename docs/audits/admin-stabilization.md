# Admin Stabilization Audit

Дата: 2026-06-29.

## Проверенные зоны

- `GET /admin/routes/eligibility` backend contract.
- `GET /admin/quality` backend contract.
- Frontend route eligibility page `/admin/routes/eligibility`.
- Shared admin API error handling.
- Authenticated production admin API watchdog.
- POI Discovery remote runner.
- Route eligibility dashboard tests.
- Admin quality resilience tests.

## Найденные причины нестабильности

| Файл | Проблема | Решение |
|---|---|---|
| `frontend/src/pages/admin/AdminRouteEligibilityPage.tsx` | Список мест и диагностика города грузились через общий `Promise.all`. Ошибка одного запроса превращала весь экран в общую ошибку, а retry отсутствовал. | Загрузка списка, диагностики и городов разделена. Каждая секция показывает собственную ошибку и кнопку повтора. |
| `frontend/src/pages/admin/AdminRouteEligibilityPage.tsx` | Таблица была без `admin-table-wrap`, на мобильном могла вылезать за экран. | Таблица списка обёрнута в `admin-table-wrap`, строки получили mobile labels. |
| `frontend/src/pages/admin/AdminRouteEligibilityDiagnostics.tsx` | Диагностические таблицы не имели mobile labels/wrapper. | Добавлены wrappers и `data-label` для мобильного представления. |
| `services/route_eligibility_dashboard/list_service.py` | Неизвестный `city_slug` возвращал список всех мест, что могло запускать тяжёлый full-catalog scan после неверного URL или устаревшей ссылки. | Неизвестный `city_slug` возвращает стабильный пустой список. |
| `services/route_eligibility_dashboard/list_service.py` | Ошибка вычисления одной строки могла уронить весь endpoint и дать 500/502 через gateway. | Добавлена admin-only изоляция строки: дефектная запись возвращается как `eligible=false`, `primary_reason=row_error`, ошибка логируется. |
| `services/admin_platform_quality.py` | `GET /admin/quality` строил весь cross-city quality payload без изоляции ошибок по городам. Ошибка deep coverage расчёта могла уронить всю вкладку качества. | Добавлена изоляция городов и degraded critical coverage contract: строка города остаётся в ответе, ошибка логируется, UI получает стабильный payload. |
| `scripts/run_poi_discovery_remote.sh` | POI discovery запускал one-off `docker compose run backend` и на `EXIT` всегда делал `docker compose up -d backend`, что могло пересоздать backend и оставить админку в `health: starting`. | Runner переведён на `docker compose exec backend ...`, больше не стартует/не пересоздаёт backend, а при ошибке печатает `POI_DISCOVERY_SUMMARY_JSON`. |
| `scripts/check_production_admin_api.py` и `.github/workflows/admin-api-watchdog.yml` | Production watchdog не проверял проблемные `/admin/routes/eligibility` и `/admin/quality`. | В watchdog добавлены `/api/admin/routes/eligibility?limit=50&offset=0` и `/api/admin/quality?`. |

## Стабилизированные API contracts

- `GET /admin/routes/eligibility?limit=50&offset=0` возвращает `200` и `{items,total,limit,offset}` даже на пустой БД.
- `GET /admin/routes/eligibility?city_slug=<missing>` возвращает пустой список, а не весь каталог.
- Дефектная запись в eligibility list больше не валит весь response; UI показывает причину `row_error`.
- `GET /admin/quality?` возвращает стабильный `{items,total,todo}` payload на пустой БД.
- Если critical coverage расчёт падает для отдельного города, `GET /admin/quality?` возвращает degraded row с `critical_coverage.degraded=true`, а не 500.
- POI Discovery больше не управляет lifecycle backend-контейнера и не должен вызывать backend restart во время admin-сессии.

## Что осталось долгом

- Computed filters (`eligible`, `readiness`, `quality`, `min_quality_score`) всё ещё могут требовать Python-прохода по большой выборке. Следующий шаг: перенести больше фильтров в SQL или добавить materialized snapshot.
- Cross-city quality всё ещё считает live summary. Для больших данных нужен materialized quality snapshot, чтобы вкладка качества не зависела от тяжёлого read-only расчёта.
- Нужно продолжить поэкранный audit для остальных admin вкладок, но текущие фиксы закрывают известные production symptoms `/admin/routes/eligibility`, `/admin/quality` и POI Discovery backend restart.
