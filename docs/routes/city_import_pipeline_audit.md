# City Import Pipeline Audit

Дата: 2026-06-08. Контекст: подготовка загрузки Алматы.

## Pipeline overview

```
OSM Overpass → import_city_osm.py → assess_import_quality → DB places
     → address enrichment → photo enrichment → verification → eligibility flags
     → publication → route generation (canonical + legacy)
```

## Этапы

### 1. OSM fetch
- **Вход:** bbox города, Overpass query
- **Выход:** raw OSM nodes/ways (`data/raw/`, `data/seeds/`)
- **Где:** `data/scripts/import_city_osm.py`, `collect_osm_*.py`, `fetch_osm_*.py`
- **Режим:** CLI, ручной запуск
- **Отказы:** Overpass rate limit, пустой bbox, timeout

### 2. Import
- **Вход:** OSM JSON
- **Выход:** `places`, `import_batches`, `place_scope_links`, `source_observations`
- **Где:** `import_city_osm.py` + `import_job_service`
- **Режим:** CLI (`python data/scripts/import_city_osm.py`)
- **Отказы:** duplicate slug, missing category mapping, DB constraint

### 3. Category Mapping
- **Вход:** OSM tags (`amenity`, `tourism`, …)
- **Выход:** canonical `place.category`
- **Где:** mapping в `import_city_osm.py`, `core/place_taxonomy.py`, `import_quality_categories.py`
- **Режим:** автоматический при импорте
- **Отказы:** unmapped tag → `unknown` / wrong tourist category

### 4. Address Enrichment
- **Вход:** places без адреса
- **Выход:** `address`, `address_source`, `address_confidence`
- **Где:** `place_address_flow_*`, `address_recovery` exports, admin `POST /admin/places/address-refresh`
- **Режим:** batch job, ручной trigger из админки
- **Отказы:** geocoder miss, low confidence

### 5. Photo Enrichment
- **Вход:** places без `image_url`
- **Выход:** `image_url` или `place_images` queue
- **Где:** `place_enrichment` batch, admin enrichment UI
- **Режим:** export → manual/AI enrich → import preview
- **Отказы:** no suitable photo, moderation reject

### 6. Verification
- **Вход:** imported / needs_review places
- **Выход:** `verification_status`, audit
- **Где:** `place_verification`, admin verification queue
- **Режим:** ручная модерация
- **Отказы:** queue backlog

### 7. Eligibility
- **Вход:** place fields + category
- **Выход:** `is_route_eligible`, `route_exclusion_reason`
- **Где:** `import_publication_gate`, `route_eligibility/`, import quality gate
- **Режим:** автоматический на импорте + admin override
- **Отказы:** legacy `is_route_eligible=true` default для старых seed

### 8. Publication
- **Вход:** quality gate decision
- **Выход:** `is_published`, `publication_status`
- **Где:** `import_publication_gate.py`, admin publish
- **Режим:** auto (high confidence) + manual
- **Отказы:** low confidence → draft

### 9. Route Generation
- **Вход:** eligible pool + request context
- **Выход:** route points + `route_generation_runs`
- **Где:** `RouteBuilderService`, legacy itinerary, `POST /admin/routes/dry-run`
- **Режим:** API
- **Отказы:** empty eligible pool, hard filters, time budget

## Дублирование / риски

- Два контура генерации (canonical vs legacy itinerary)
- Eligibility: SQL strict vs flag `is_route_eligible` на legacy data
- Category errors propagate to routes if not caught at import

## Рекомендации для Алматы

1. Создать город `almaty` до импорта
2. Прогнать OSM import с `assess_import_quality` — проверить NON_TOURIST mapping
3. После импорта: Data Quality + Eligibility dashboard
4. Dry-run до включения `route_generation_enabled` для города
5. Address/photo enrichment batch до publish массового
