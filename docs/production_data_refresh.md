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
