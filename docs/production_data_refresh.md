# City Go — Production Data Import and Image Refresh

Дата: 2026-06-05.

## Place Import

Dry-run по умолчанию:

```bash
.venv/bin/python scripts/production_place_import.py --api-base http://127.0.0.1:8000
```

Real import только явно:

```bash
.venv/bin/python scripts/production_place_import.py --api-base https://api.example.com --real
```

Seed-пакеты по умолчанию:

- `data/seeds/place_import/zelenogradsk_osm.json`
- `data/seeds/place_import/zelenogradsk_editorial_walks.json`

После real import:

```bash
.venv/bin/python scripts/check_place_coverage_gate.py zelenogradsk
```

## One-click OSM Import

Ручной OSM-импорт Астрахани запускается через GitHub Actions workflow
`Import Astrakhan OSM`.

Workflow не запускает importer напрямую в backend container. Он через production
host проверяет `/ready`, находит город через
`/admin/cities/by-slug/astrakhan/workspace`, ставит существующую
`/admin/import-jobs/{city_id}/run` в очередь и читает
`/admin/import-jobs/{city_id}`.

Компактный отчёт строится на GitHub runner командой:

```bash
python3 scripts/build_import_status_summary.py < import-status.json
```

В логах нужно смотреть:

- `Run request status`: `2xx` означает, что задача поставлена в очередь; `409`
  означает, что задача уже активна, готова к проверке или завершена.
- `job_status`, `current_step`, `launch_status`.
- `created`, `updated`, `rejected`, `hidden`, `needs_review`,
  `changed_place_ids_count`, `warnings_count`.

## Import Run Report

Import Run Report показывает, какие места относятся к конкретному запуску
admin import job. Он нужен, чтобы новые и изменённые места не терялись в общей
очереди проверки, где могут быть сотни старых `needs_review` записей.

Смотреть отчёт можно через admin API:

- `/admin/import-jobs/{city_id}/changes/summary` — счётчики конкретного job.
- `/admin/import-jobs/{city_id}/changes?change_type=created` — список мест или
  кандидатов с фильтром по типу изменения.

Счётчики:

- `created` — новые места, созданные этим прогоном.
- `updated` — существующие места, обновлённые этим прогоном.
- `unchanged` — найденные, но не изменённые места.
- `needs_review` — места, которые нужно проверить вручную.
- `hidden` — места, скрытые lifecycle-правилами.
- `rejected` — кандидаты, которые не стали `Place`.

Это не то же самое, что общая очередь проверки: очередь показывает все места,
ожидающие ручного решения, а Import Run Report привязан к одному import job и
помогает понять результат именно этого запуска.

## Admin Background Refresh Contract

Для тяжёлых admin-процессов действует правило:

```text
GET = только чтение сохранённого snapshot/list.
POST = постановка тяжёлой операции в background job.
UI = показывает last_snapshot_at, freshness, running/failed и кнопку обновления.
```

Запрещённый паттерн:

```text
GET /admin/...?...refresh=true -> live refresh/rebuild/recalculate
```

Текущие background endpoints:

```text
POST /admin/background-operations/coverage-gaps/refresh
GET  /admin/background-operations/coverage-gaps/status?city_slug=<slug>
POST /admin/background-operations/city-readiness/recalculate
GET  /admin/background-operations/city-readiness/status?city_slug=<slug>
GET  /admin/background-operations/{operation_id}
GET  /admin/background-operations/latest/status?operation_type=<type>&city_slug=<slug>
```

Compatibility endpoints, которые теперь должны возвращать быстро и не держать
браузерный запрос:

```text
POST /admin/routes/readiness/{city_slug}/recalculate
POST /admin/places/address-refresh
```

Оба endpoint только создают `admin_operations` и возвращают `operation_id`.
Фактическая работа выполняется через background task.

## Image Refresh

Локальный refresh без live network:

```bash
.venv/bin/python scripts/refresh_place_images.py
```

Live refresh:

```bash
.venv/bin/python scripts/refresh_place_images.py --live
```

С Mapillary:

```bash
.venv/bin/python scripts/refresh_place_images.py --live --mapillary-token "$MAPILLARY_TOKEN"
```

Токен передаётся явно в процесс и не сохраняется в коде, логах или документах.

## Safety

- Google/Yandex/2GIS scraping не используется.
- Category/area images не маркируются как exact place photo.
- `validate_catalog_images.py` запускается после refresh и возвращает ошибки в JSON.
