# Аудит pipeline обогащения данных — текущее состояние

Дата: 2026-06-08. Только факты по коду и эксплуатации prod.

## 1. Карта pipeline (фактическая)

```
Админ: POST /admin/cities/import
  → City (launch_status=importing, is_active=false)
  → CityImportScope ×3 (enabled, не published)
  → CityAdminImportJob (queued)
  → import-worker / run_admin_import_queue / run_city_import_once
  → run_due_import_jobs --apply --city <slug>
       → import_city_osm.py (Overpass, per scope)
       → cleanup_imported_places_quality (опционально)
       → backfill_missing_place_addresses (limit=100, apply если в runner)
  → city.launch_status = imported | import_failed
  → publish_city.py (ручной) → published + is_active=true

Параллельно НЕ в цепочке автоматически:
  → enrich_place_images.py (ручной, --apply)
  → run_place_enrichment_export.py → ChatGPT CSV → import_place_enrichment_csv
  → image_pipeline/run.py → frontend/public/data/*.json (static)
  → address recovery flow (dry-run в docker profile ops)
```

## 2. Импорт города

| Что | Где | Факт |
|-----|-----|------|
| Создание | `services/admin_service.create_city_and_queue_import` | slug из кириллицы без транслитерации (`алматы`) |
| Scopes | `admin_city_import_setup.finish_city_import_setup` | tourist_core, food_area, useful_services |
| Очередь | `city_admin_import_jobs` | статусы: queued, running, success, failed |
| Worker | `docker-compose` service `import-worker` | каждые 5 мин, limit=3 |
| OSM | `data/scripts/import_city_osm.py` | dry-run XOR apply; max 2500 raw objects |
| После успеха | `admin_city_import_job_finish` | `launch_status=imported`, город **не** публикуется |
| Публикация города | `publish_city.py` / ручной шаг | `published`, `is_active=true` |

**Ручные шаги:** публикация города, scope publish, массовая модерация мест.

**Потери данных:** OSM `website`, `phone` нормализуются, но в `Place` не пишутся (нет полей).

## 3. Адреса

| Источник | Модуль | Apply |
|----------|--------|-------|
| OSM tags | `import_city_osm._address()` | при import apply |
| Nominatim | `backfill_missing_place_addresses.py` | только с `--apply` |
| Recovery CSV | `run_address_recovery_flow.py` | `--apply-from-review` |
| Enrichment CSV | `suggested_address` | enrichment apply |

**Почему без адреса:** OSM без addr:*; backfill limit=100 за прогон; docker `address-backfill` в profile `ops` по умолчанию **без apply**; `address_source`/`address_confidence` при Nominatim **не заполняются**.

## 4. Фото

| Трек | Куда пишет | Автоматизация |
|------|------------|---------------|
| `image_pipeline/run.py` | `frontend/public/data/*.json` | ручной, не PostgreSQL |
| `enrich_place_images.py` | `place_images` + `place.image_url` | ручной `--apply`, auto-approve |
| CSV `suggested_image_url` | — | **skipped** (`skipped_requires_image_pipeline`) |

**Почему без фото:** import не тянет фото в PG; pipeline static; enrichment CSV не создаёт `place_images`; публичный API берёт approved `place_images` или legacy `image_url`.

## 5. Описания

| Источник | Поведение |
|----------|-----------|
| OSM import | шаблон `«Кафе: {name}»` — поле **не пустое** |
| Enrichment export | missing `description` = `short_description IS NULL` → OSM-места **не попадают** в export |
| CSV apply | `suggested_short_description` → `short_description` ✅ |

**Вывод:** автоматических качественных описаний нет; ChatGPT только через ручной CSV.

## 6. Категории

| Путь | Маппинг |
|------|---------|
| **Prod import** | `import_city_osm._category()` → cafe, culture, viewpoint, useful, health (вне канона) |
| **Канон** | `core/place_taxonomy.PLACE_CATEGORIES` |
| **Seed** | `osm_seed_builder.TYPE_TO_CATEGORY` — другой маппинг |

Import **не вызывает** `place_taxonomy_service`. Route eligibility терпит legacy-строки через aliases.

## 7. Теги

Таблицы: `tags`, `place_tags`. OSM import и seed **не пишут** теги. Admin bulk — пишет. Route scoring через `place.tags` — **атрибут не существует** на ORM → interest-by-tags no-op.

## 8. Публикация мест

| Поле | Роль |
|------|------|
| `publication_status` | draft / published / needs_review / hidden |
| `is_published`, `is_visible_in_catalog` | публичный каталог |
| `is_route_eligible` | маршруты |
| `verification_status` | верификация ≠ публикация |

Gate: `import_publication_gate.assess_import_quality` при import. Re-import **не меняет** publication flags.

**Факт prod:** много `published` + `unverified` — gate и legacy defaults.

## 9. Разрывы (что ломает качество)

1. Контуры не сшиты: import завершён ≠ адреса ≠ фото ≠ описания ≠ quality.
2. `suggested_image_url` silently skipped.
3. Два taxonomy map + non-canonical categories в БД.
4. Static image pipeline ≠ PostgreSQL.
5. Enrichment export по description бесполезен для OSM-мест.
6. Теги не импортируются и не влияют на маршруты.
7. Import job UX: нет шагов address/photo/description/quality.
8. Slug кириллицей (`алматы`) — техдолг URL/API.

## 10. Ручные vs автоматические шаги

| Шаг | Сейчас |
|-----|--------|
| Импорт OSM | авто (worker) |
| Адреса apply | частично (limit 100), иначе ручной |
| Фото PG | ручной |
| Описания | ручной CSV/ChatGPT |
| Категории fix | ручной |
| Теги | не реализовано |
| Quality/readiness | API есть, пересчёт не в pipeline |
| Публикация города | ручной |
| Публикация мест | gate + ручная модерация |

## 11. Связанные модули

- `data/scripts/import_city_osm.py`, `run_due_import_jobs.py`, `run_admin_import_queue.py`
- `data/scripts/backfill_missing_place_addresses.py`, `enrich_place_images.py`
- `data/scripts/run_place_enrichment_export.py`, `import_place_enrichment_csv.py`
- `services/place_enrichment_import/field_map.py`
- `services/import_publication_gate.py`, `place_import_lifecycle_service.py`
- `docs/architecture/place_data_enrichment.md`, `place_address_lifecycle.md`

## 12. Целевое состояние (для следующих блоков)

Единый pipeline с бизнес-статусами шагов, apply адресов/фото в PG, явные skipped reasons, quality/readiness после каждого шага, ручная публикация города только после readiness.
