# Admin Stabilization Audit

Дата: 2026-06-29.

## Проверенные зоны

- `GET /admin/routes/eligibility` backend contract.
- Frontend route eligibility page `/admin/routes/eligibility`.
- Shared admin API error handling.
- Authenticated production admin API watchdog.
- Route eligibility dashboard tests.

## Найденные причины нестабильности

| Файл | Проблема | Решение |
|---|---|---|
| `frontend/src/pages/admin/AdminRouteEligibilityPage.tsx` | Список мест и диагностика города грузились через общий `Promise.all`. Ошибка одного запроса превращала весь экран в общую ошибку, а retry отсутствовал. | Загрузка списка, диагностики и городов разделена. Каждая секция показывает собственную ошибку и кнопку повтора. |
| `frontend/src/pages/admin/AdminRouteEligibilityPage.tsx` | Таблица была без `admin-table-wrap`, на мобильном могла вылезать за экран. | Таблица списка обёрнута в `admin-table-wrap`, строки получили mobile labels. |
| `frontend/src/pages/admin/AdminRouteEligibilityDiagnostics.tsx` | Диагностические таблицы не имели mobile labels/wrapper. | Добавлены wrappers и `data-label` для мобильного представления. |
| `services/route_eligibility_dashboard/list_service.py` | Неизвестный `city_slug` возвращал список всех мест, что могло запускать тяжёлый full-catalog scan после неверного URL или устаревшей ссылки. | Неизвестный `city_slug` возвращает стабильный пустой список. |
| `services/route_eligibility_dashboard/list_service.py` | Ошибка вычисления одной строки могла уронить весь endpoint и дать 500/502 через gateway. | Добавлена admin-only изоляция строки: дефектная запись возвращается как `eligible=false`, `primary_reason=row_error`, ошибка логируется. |
| `scripts/check_production_admin_api.py` и `.github/workflows/admin-api-watchdog.yml` | Production watchdog не проверял проблемный `/admin/routes/eligibility`. | В watchdog добавлен `/api/admin/routes/eligibility?limit=50&offset=0`. |

## Стабилизированные API contracts

- `GET /admin/routes/eligibility?limit=50&offset=0` возвращает `200` и `{items,total,limit,offset}` даже на пустой БД.
- `GET /admin/routes/eligibility?city_slug=<missing>` возвращает пустой список, а не весь каталог.
- Дефектная запись в eligibility list больше не валит весь response; UI показывает причину `row_error`.

## Что осталось долгом

- Computed filters (`eligible`, `readiness`, `quality`, `min_quality_score`) всё ещё могут требовать Python-прохода по большой выборке. Следующий шаг: перенести больше фильтров в SQL или добавить materialized snapshot.
- Нужно продолжить поэкранный audit для остальных admin вкладок, но текущий фикс закрывает известный production symptom `/admin/routes/eligibility` и watchdog coverage.
