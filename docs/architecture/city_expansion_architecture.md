# City Expansion Architecture

## Registry

`countries`, `regions`, `city_candidates` и расширенный `cities` разделяют подготовленные города и опубликованные города продукта. `city_candidates` не показываются пользователю как доступные города.

`GET /cities/available` возвращает только `launch_status=published` и `is_active=true`, если не передан debug/admin флаг `include_draft=true`.

## Import Scopes

`city_import_scopes` задают зоны частичного импорта. Новые города расширяются добавлением scopes, а не full-city import. Overlapping scopes допустимы; `place_scope_links` фиксирует связь place/scope и предотвращает повторную связь.

## Import State

`city_import_jobs`, `import_batches` и `city_scope_import_state` дают cron-ready слой. Cron читает due enabled scopes, ставит lock, создаёт batch, обновляет state и снимает lock. Ошибка batch не трогает production places.

`data/scripts/run_due_import_jobs.py` — текущая production entrypoint для cron.
Он читает `data/config/import_targets.json`, фильтрует `--city/--scope`, уважает
`next_run_at`, ставит scope lock и запускает `import_city_osm.py`. `--force`
нужен только для ручного запуска вне расписания.

Admin-created city imports are described in
[`city_import_pipeline.md`](city_import_pipeline.md): queued jobs, blocking vs
non-blocking steps, stalled detection, low-yield bbox fallback and publication
flow.

## Source Observations

`source_observations` хранит все raw objects, включая rejected/profile_excluded/outside_scope. `rejection_reason` обязателен для объяснимой отбраковки.

## Missing Place Queue

`place_discovery_requests` хранит “места нет в каталоге” из UI, Telegram, редактора или raw import. Запрос не создаёт published place.

## Source Presence

`place_source_presence` отслеживает исчезновение source object. Один пропуск даёт `missing_once`, повторные пропуски — `missing_repeatedly`/`possible_removed`, но не delete.

OSM apply-import после каждого batch сравнивает увиденные source ids с ранее
связанными places внутри scope. Неувиденные объекты только повышают
`consecutive_missing_count`; автоматического удаления нет.

## Route Safety

Candidate retrieval теперь использует только published active cities. Places из unpublished scopes не попадают в маршруты. Legacy places без scope links остаются видимыми, чтобы Зеленоградск не сломался.

## Telegram City Selection

Telegram хранит `selected_city_slug` в `telegram_user_contexts`. `/start` без города показывает выбор города. Draft cities показываются как “готовится” и не используются для маршрутов.
