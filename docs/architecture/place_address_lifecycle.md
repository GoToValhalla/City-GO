# Place Address Lifecycle

## Источники адреса

| Источник | Как попадает | Надёжность |
|----------|-------------|-----------|
| OSM import | Парсинг `addr:*` и `contact:*` тегов | Высокая |
| Nominatim backfill | Reverse geocoding по lat/lng | Средняя |
| Address recovery flow | coverage → dry-run → review → apply-from-review | Средняя (только `should_apply=true`) |
| Ручной ввод (admin panel) | Прямое редактирование | Высокая |
| Place enrichment import | `suggested_address` → `Place.address` через import apply | Средняя (требует preview) |
| Seed import (CSV/JSON) | Поле `address` из файла | Зависит от источника |

> Enrichment workflow: см. `docs/architecture/place_data_enrichment.md`

---

## Как адрес попадает из OSM

Парсер адреса в `data/scripts/import_city_osm.py::_address()`:

```
1. Structured address (приоритетнее):
   addr:street  или  contact:street
   addr:housenumber  или  contact:housenumber
   addr:city  /  addr:town  /  addr:village  /  contact:city

2. Place fallback (если нет street):
   addr:place  [+  city]

3. Full address fallback (если нет structured данных):
   addr:full  /  contact:address
```

Если нет ни одного тега — `address` остаётся **пустым** (`""` / `NULL`). Адрес **не придумывается**.

---

## Если адреса нет

| Слой | Поведение |
|------|-----------|
| БД | `address` пустой или плейсхолдер очищен в `""` |
| API | поле `address` может быть `null` / `""` |
| UI | текст **«Адрес уточняется»**, ссылки на карту по `lat`/`lng` |
| Маршрут | место не скрывается; navigation URLs строятся по координатам |

Запрещено хранить в БД литерал **«Адрес не указан»**.

---

## Поля Place

| Поле | Назначение |
|------|-----------|
| `address` | Единственное человекочитаемое поле адреса |
| `lat`, `lng` | Координаты (обязательны для import) |

---

## Политика адресов

Модуль: `services/place_address_policy.py`

| Функция | Назначение |
|---------|-----------|
| `is_real_address` | не пустой и не плейсхолдер |
| `is_generic_address` | слишком общий текст (`центр города`, `променад`, `пляж`, `набережная`, короткий без улицы для cafe/food/museum) |
| `needs_backfill` | пустой или плейсхолдер |
| `needs_recovery` | backfill или (с `--include-generic`) generic |
| `is_replaceable_address` | можно заменить при apply (пустой/плейсхолдер/generic) |
| `should_apply_geocode_result` | не применять city-only для заведений |

**Запрещено:**
- «Адрес не указан» в БД
- выдуманные адреса без источника
- city-only результат для cafe/food/restaurant/museum

**Разрешено для culture/walk/park/viewpoint:** улица без номера, если это не просто название города.

---

## Automatic address recovery flow

Оркестратор: `data/scripts/run_address_recovery_flow.py`  
Сервис: `services/place_address_flow.py`

```bash
# Только отчёт (БД не меняется)
python data/scripts/run_address_recovery_flow.py --all-cities --limit 500 --sleep 1.0

# Локальный apply (только should_apply=true из review CSV)
python data/scripts/run_address_recovery_flow.py --all-cities --limit 500 --sleep 1.0 --apply
```

### Этапы

```
import / seed / enrichment
  → address coverage check (check_place_address_coverage.py --export)
  → address recovery dry-run (Nominatim reverse)
  → review artifact (CSV + JSON)
  → safe apply (--apply-from-review, only should_apply=true)
  → apply_result.json
  → coverage after
  → flow summary JSON
```

### Артефакты (`data/exports/address_recovery/`, в `.gitignore`)

| Файл | Содержимое |
|------|-----------|
| `address_coverage_before_*.json` | метрики до recovery |
| `address_recovery_<city>_*.csv` | построчный review |
| `address_recovery_<city>_*.json` | summary dry-run |
| `address_recovery_<city>_*.csv.apply_result.json` | результат apply |
| `address_coverage_after_*.json` | метрики после |
| `address_recovery_flow_*.json` | общий summary по всем городам |

### Флаги flow

| Флаг | Default | Описание |
|------|---------|----------|
| `--all-cities` | — | все города в БД |
| `--city <slug>` | — | один или несколько городов |
| `--limit` | 500 | макс. мест на город |
| `--sleep` | 1.0 | пауза между Nominatim-запросами |
| `--dry-run` | да (без `--apply`) | preview без записи |
| `--apply` | нет | apply-from-review |
| `--no-apply` | — | явный режим только отчёта |
| `--include-generic` | авто для городов с generic>0 | recovery generic-адресов |

### Когда запускать

- после city OSM import
- после seed load
- после place enrichment import
- перед route quality check / coverage audit

### Что flow **не** делает

- не ищет сайты и фото
- не меняет маршруты
- не деплоит
- не трогает production DB без отдельной задачи

### Production apply (позже)

1. Запустить flow **без** `--apply` на сервере или экспортировать review artifacts
2. Проверить summary и CSV
3. Apply — отдельная операция с явным подтверждением (изменение production DB)

---

## Nominatim User-Agent

Переменная: `PLACE_ADDRESS_GEOCODER_USER_AGENT`  
Модуль: `services/place_address_geocode.py`

- default: `CityGoAddressBackfill/1.0`
- значения с `example.com` **отклоняются** (OSMF 403)
- **не использовать** `citygo@example.com`

---

## Диагностика

```bash
python data/scripts/check_place_address_coverage.py --export
```

Метрики на город: `total_places`, `published_places`, `visible_in_catalog`, `route_eligible`, `with_real_address`, `without_address`, `generic_address_count`, `literal_placeholder_count`, `empty_address_count`, `samples_missing`, `samples_generic`.

API: `GET /place-coverage/{city_slug}` → `with_address` / `without_address`.

---

## Ручные CLI

```bash
# Dry-run + review export
python data/scripts/backfill_missing_place_addresses.py \
  --city zelenogradsk --limit 500 --sleep 1.0 --dry-run --export-review --include-generic

# Apply из review
python data/scripts/backfill_missing_place_addresses.py \
  --city zelenogradsk --apply-from-review data/exports/address_recovery/address_recovery_zelenogradsk_*.csv

# Очистка плейсхолдеров
python data/scripts/backfill_missing_place_addresses.py --city <slug> --clear-placeholders --apply
```
