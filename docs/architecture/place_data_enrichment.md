# Place Data Enrichment — Architecture

## Цель

Позволить операторам выгружать список мест с пустыми полями в CSV-файл, который затем
передаётся в ChatGPT или другой инструмент для заполнения недостающих данных.
После обогащения enriched CSV импортируется обратно через preview/apply (CLI или admin UI).

---

## Общий Flow

### Автоматический (после deploy / import)

```
docker compose up place-enrichment-export
    → data/scripts/run_place_enrichment_export.py
    → --limit 100 --missing-fields address,photo,description --git-artifact
    → создаёт CSV для каждого города в БД
    → CSV сохраняется в active/<batch_id>/export.csv
    → виден в /admin/place-enrichment и в GitHub после commit
```

### Ручной через Quick Action

```
/admin/place-enrichment → кнопка "Сформировать стандартный экспорт"
    → POST /admin/place-enrichment/export
    → limit=100, missing_fields=[address, photo, description], only_published=true
    → CSV доступен сразу в таблице экспортов
```

### Ручной с кастомными параметрами

```
/admin/place-enrichment → форма
    → выбор города, лимит, missing_fields (чекбоксы)
    → POST /admin/place-enrichment/export
    → CSV скачивается кнопкой "↓ CSV"
    → передаётся в ChatGPT / таблицу
    → заполняются suggested_* колонки
    → import preview/apply через CLI или admin UI
```

### Стандартный набор полей (auto + quick action)

| Поле | Почему важно |
|------|-------------|
| `address` | Большинство мест из OSM не имеют адреса |
| `photo` | `image_url` пустой у >80% мест |
| `description` | `short_description` — технический префикс ("Кафе: Ассорти") |

---

## GitHub batch storage

```
data/exports/place_enrichment/
  README.md
  active/<batch_id>/
    export.csv           ← Cursor создаёт, НЕ перезаписывать
    export.meta.json
    enriched.csv         ← ChatGPT создаёт
    import.preview.json  ← Cursor preview
    import.result.json   ← Cursor apply
  archive/<batch_id>/    ← после успешного import
```

`batch_id` = `place_enrichment_<city_slug>_<YYYYMMDD_HHMMSS>`

Статусы: `exported` → `enriched` → `previewed` → `imported` | `failed`

После успешного apply batch **полностью** переносится `active/<batch_id>/` → `archive/<batch_id>/`
(все 5 файлов: export.csv, export.meta.json, enriched.csv, import.preview.json, import.result.json).
Meta со статусом `imported` пишется в **active** до переноса; `write_batch_meta` не создаёт archive dir заранее.

Repair без БД: `python data/scripts/import_place_enrichment_csv.py --batch-id <id> --repair-archive`

### Server apply (archived batch, без пересоздания export)

Archived batch из GitHub читается import-скриптом напрямую (`resolve_batch_paths` → `archive/`).
Volume `enrichment_exports` перекрывает файлы образа — для apply используйте `docker run` **без** volume
(см. `data/scripts/server_apply_archived_enrichment.sh`).

```bash
# preview (не меняет БД)
docker run --rm --env-file .env --network app_default IMAGE \
  bash -c 'PYTHONPATH=/app python data/scripts/import_place_enrichment_csv.py \
    --batch-id place_enrichment_khanty-mansiysk_20260607_160951 --preview'

# apply (только после preview без errors)
docker run --rm --env-file .env --network app_default IMAGE \
  bash -c 'PYTHONPATH=/app python data/scripts/import_place_enrichment_csv.py \
    --batch-id place_enrichment_khanty-mansiysk_20260607_160951 --apply --no-archive-if-archived'
```

Проверка БД: `data/scripts/verify_enrichment_apply.py --city-slug <slug> --batch-id <id>`

Volume `enrichment_exports` в Docker Compose shared между `place-enrichment-export` и `backend`.
Для ChatGPT workflow — commit `active/<batch_id>/export.csv` + `export.meta.json` в GitHub.

---

## Скрипт

```
data/scripts/run_place_enrichment_export.py
```

| Параметр | По умолчанию | Описание |
|----------|-------------|----------|
| `--city` | все города | Slug города (опционально) |
| `--limit` | 100 | Максимум мест за один запуск |
| `--only-published` | true | Только опубликованные |
| `--only-route-eligible` | false | Только route-eligible |
| `--missing-fields` | `address,photo,description` | Запятая-разделённый список |
| `--git-artifact` | true | Создать batch в active/ (default) |

```bash
# Пример запуска
PYTHONPATH=/app python data/scripts/run_place_enrichment_export.py \
    --city zelenogradsk --limit 50 --missing-fields address,photo
```

---

## Backend

### Модули

| Файл | Ответственность |
|------|----------------|
| `schemas/place_enrichment.py` | Pydantic-схемы запросов и ответов |
| `services/place_enrichment_query.py` | Фильтрация мест по наличию пустых полей |
| `services/place_enrichment_csv.py` | Определение колонок CSV и построение строк |
| `services/place_enrichment_service.py` | Оркестрация export → batch artifacts → audit |
| `services/place_enrichment_batch/` | paths, meta, archive (active/archive storage) |
| `services/place_enrichment_import/` | field_map, parse_values, preview_builder, apply_changes |
| `services/place_enrichment_import_service.py` | Import preview/apply orchestration |
| `data/scripts/run_place_enrichment_export.py` | CLI export (`--git-artifact`) |
| `data/scripts/import_place_enrichment_csv.py` | CLI import (`--preview` / `--apply`) |
| `routers/place_enrichment.py` | Admin API (7 endpoints) |

### Эндпоинты

| Method | Path | Описание |
|--------|------|----------|
| `POST` | `/admin/place-enrichment/export` | Создать batch в `active/<batch_id>/` |
| `GET` | `/admin/place-enrichment/batches` | Список batch (active + archive) |
| `GET` | `/admin/place-enrichment/exports` | Legacy-совместимый список (из batches) |
| `GET` | `/admin/place-enrichment/exports/{id}/download` | Скачать `export.csv` по batch_id |
| `GET` | `/admin/place-enrichment/batches/{id}/files/{filename}` | Скачать artifact (export/enriched/preview/result) |
| `POST` | `/admin/place-enrichment/batches/{id}/preview` | Preview import → `import.preview.json` |
| `POST` | `/admin/place-enrichment/batches/{id}/apply` | Apply import → БД + audit + archive |

`POST /export` параметры: `city_slug`, `limit` (1–500), `only_published`, `only_route_eligible`,
`missing_fields`, `git_artifact` (default `true`). Сохраняет `active/<batch_id>/export.csv` +
`export.meta.json`. Audit: `action=place_enrichment_export`, `entity_type=place_enrichment_batch`.

---

## CSV-структура

### Текущие данные (`current_*`)

Заполняются из БД на момент экспорта:

| Колонка | Источник в Place |
|---------|-----------------|
| `current_address` | `place.address` |
| `current_image_url` | `place.image_url` |
| `current_short_description` | `place.short_description` |
| `current_opening_hours` | `place.opening_hours` (JSON) |
| `current_price_level` | `place.price_level` |
| `current_dog_friendly` | `place.dog_friendly` |
| `current_website` | *(нет в модели, пустое)* |
| `current_phone` | *(нет в модели, пустое)* |

### Поля для обогащения (`suggested_*`)

Всегда пустые при выгрузке — заполняются оператором или AI:

- `suggested_address`, `suggested_website`, `suggested_phone`
- `suggested_opening_hours`, `suggested_menu_url`, `suggested_social_links`
- `suggested_image_url`, `suggested_short_description`
- `suggested_price_level`, `suggested_dog_friendly`, `suggested_family_friendly`
- `suggested_outdoor`, `suggested_indoor`
- `suggested_cuisine`, `suggested_average_check`
- `suggested_source_url`, `suggested_data_source`, `suggested_confidence`
- `suggested_comment`
- **Кафе/бары**: `suggested_takeaway`, `suggested_delivery`, `suggested_reservation_url`
- **Музеи/культура**: `suggested_ticket_url`, `suggested_ticket_price`, `suggested_exhibition_url`
- **Парки/пляжи/прогулки**: `suggested_facilities`, `suggested_seasonality`, `suggested_accessibility`

> Все `suggested_*` колонки присутствуют в каждом файле независимо от категории.

---

## Определение "отсутствует" (missing_fields)

| Поле | Условие |
|------|---------|
| `address` | `place.address` пустое или `None` |
| `photo` | `place.image_url` is `None` |
| `description` | `place.short_description` is `None` |
| `opening_hours` | `place.opening_hours` is `None` |
| `price_level` | `place.price_level` is `None` |
| `dog_friendly` | `place.dog_friendly == False` |
| `family_friendly` | `place.family_friendly == False` |
| `outdoor` | `place.outdoor == False` |
| `indoor` | `place.indoor == False` |
| `website`, `phone`, `menu_url`, `social_links` | Всегда `True` (нет в модели) |

---

## Frontend

Страница `/admin/place-enrichment`:

- **Quick Action** — стандартный export (limit 100, address/photo/description)
- **Кастомная форма** — город, лимит, `only_published`, `only_route_eligible`, missing_fields
- **ChatGPT path hint** — после export показывает путь `active/<batch_id>/export.csv`
- **Таблица batches** — batch_id, status, файлы (export/enriched/preview/result), Preview/Apply
- Компоненты: `AdminPlaceEnrichmentPage.tsx`, `AdminEnrichmentBatchTable.tsx`,
  `adminEnrichmentForm.ts`, `adminEnrichmentTypes.ts`, `adminEnrichmentHelpers.ts`

---

## Audit Log

Каждый экспорт фиксируется в `admin_audit_logs`:

```json
{
  "actor": "admin",
  "action": "place_enrichment_export",
  "entity_type": "place_enrichment_batch",
  "entity_id": "<batch_id>",
  "new_value": {
    "city_slug": "zelenogradsk",
    "limit": 100,
    "missing_fields": ["address", "photo"],
    "total_exported": 47
  }
}
```

---

## Import back (preview + apply)

Скрипт: `data/scripts/import_place_enrichment_csv.py`

```bash
# Preview — не меняет БД, создаёт import.preview.json
python data/scripts/import_place_enrichment_csv.py --batch-id <batch_id> --preview

# Apply — применяет изменения, audit log, archive batch
python data/scripts/import_place_enrichment_csv.py --batch-id <batch_id> --apply
```

Admin API:
- `POST /admin/place-enrichment/batches/{batch_id}/preview`
- `POST /admin/place-enrichment/batches/{batch_id}/apply`
- `GET /admin/place-enrichment/batches/{batch_id}/files/{filename}`

### Импортируемые поля (apply)

| suggested_* | Place field |
|-------------|-------------|
| suggested_address | address |
| suggested_short_description | short_description |
| suggested_price_level | price_level |
| suggested_dog/family/outdoor/indoor | bool flags |
| suggested_opening_hours | opening_hours (JSON) |

### Skipped на первом этапе

| suggested_* | Причина |
|-------------|---------|
| suggested_image_url | skipped_requires_image_pipeline |
| suggested_website, phone, menu_url, social_links | skipped_unsupported_field (нет в Place) |
| cuisine, average_check, ticket_*, facilities и др. | skipped_unsupported_field |

Import audit: `action=place_enrichment_import`, `entity_type=place_enrichment_batch`.

---

## Тесты

| Файл | Покрытие |
|------|----------|
| `tests/test_place_enrichment_new.py` | API export/list/download, permissions, audit |
| `tests/test_place_enrichment_batch_new.py` | batch storage, preview/apply, archive |
| `tests/test_place_enrichment_script_new.py` | CLI export script |
| `frontend/src/pages/admin/adminEnrichment_new.test.tsx` | Quick export, batch table, Preview/Apply UI |

```bash
python3.11 -m pytest tests/test_place_enrichment_new.py tests/test_place_enrichment_batch_new.py tests/test_place_enrichment_script_new.py -q
cd frontend && npm run test -- adminEnrichment_new.test.tsx
```

---

## Ограничения

- Backend **не обращается** к внешним API при export
- Export **не изменяет** БД
- `export.csv` **никогда не перезаписывается** — только новый batch_id
- Apply **требует preview** (или auto-preview при apply)
- Фото импортируются отдельной задачей через image pipeline
