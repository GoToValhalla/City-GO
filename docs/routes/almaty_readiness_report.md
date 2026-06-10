# Алматы — Route Operations Readiness

Дата: 2026-06-08.

## 1. Что готово для загрузки

| Компонент | Статус |
|-----------|--------|
| Route Eligibility rules + SQL filters | ✅ |
| Generation diagnostics (`route_generation_runs`) | ✅ |
| Admin Dry Run API + UI | ✅ |
| Eligibility Dashboard API + UI | ✅ |
| Data Quality API + UI | ✅ |
| City Readiness Score + карточка в Города | ✅ |
| Place Quality Score | ✅ |
| Import pipeline audit doc | ✅ |
| Bulk exclude/enable route (admin) | ✅ |

## 2. Что не готово

| Компонент | Статус |
|-----------|--------|
| Город `almaty` в БД | ❌ не создан |
| OSM import для Алматы | ❌ не запускался |
| Алматы-specific category tuning | ❌ |
| Retention job для diagnostics | ❌ (документировано) |
| Unified legacy→canonical route engine | ❌ (следующий этап) |
| UI: edit category/tags inline в Eligibility table | ⚠️ через карточку места |

## 3. Ручные операции после импорта

1. Проверка Data Quality → suspicious/forbidden categories
2. Bulk exclude служебных POI из Eligibility dashboard
3. Address refresh batch
4. Photo enrichment export/import
5. Verification queue для low-confidence
6. Dry-run нескольких сценариев (duration, interests)
7. Включение `route_generation_enabled` для `almaty` после readiness `needs_review`+

## 4. Узкие места пайплайна

- Overpass rate limits на большой bbox Алматы
- Category mapping OSM → canonical (риск service POI как tourist)
- Photo enrichment — ручной цикл
- `is_route_eligible` default на legacy path
- Quality buckets на sample 2000 (большой город — approximation)

## 5. Автоматизация без ручного вмешательства

**Полностью автоматически:**
- OSM import + quality gate + eligibility flags для mapped categories
- SQL exclusion forbidden categories из маршрутов
- Diagnostics на каждую генерацию

**Требует ручной проверки:**
- Фото (~100% новых мест без фото после OSM)
- Описания (если не в OSM)
- Верификация low-confidence
- Публикация draft places
- Category fixes для mis-tagged POI

**Оценка:** ~60–70% мест пройдут import автоматически; ~30–40% потребуют enrichment/moderation до хорошего route pool.

## 6. Первый полный прогон Алматы

```bash
# 1. Создать город: Admin → Города → форма «Добавить город»
#    (POST /admin/cities/import: геокодинг + import scopes в БД)
# 2. Импорт OSM (cron run_due_import_jobs подхватит scopes из БД)
python data/scripts/import_city_osm.py --city-slug almaty ...

# 3. Проверки
GET /admin/routes/data-quality/almaty
GET /admin/routes/readiness/almaty
POST /admin/routes/dry-run { "city_slug": "almaty", "duration_min": 180 }

# 4. Enrichment
# Admin → Обогащение данных → export/import

# 5. Enable toggles
# Admin → Города → route_generation_enabled
```

**Критерий готовности к публичным маршрутам:**
- Readiness status ≥ `needs_review`
- eligible_places ≥ 30
- Dry-run возвращает ≥ 3 selected без forbidden categories
