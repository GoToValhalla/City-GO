# City Go — Data Quality Layer

Последнее обновление: 2026-06-18

Документ фиксирует архитектурный аудит первого этапа разработки City Go: данные и качество каталога.

## 0. Честный диагноз

### 0.1. Есть pipeline, но нет data contract

В проекте уже есть enrichment pipeline и OSM ingestion, но не зафиксировано, что именно считается готовым местом. Из-за этого route builder, coverage report и UI опираются на разные implicit-требования к качеству данных.

### 0.2. Quality Score без enforcement бесполезен

Если качество только считается, но не влияет на публикацию места, публикацию города и попадание места в маршрут, это декоративная метрика. Нужен quality gate: ниже порога — не публикуется или не попадает в маршруты.

### 0.3. Масштаб 100+ городов требует другой операционной модели

Ручные операции не масштабируются. При 100 городах human intervention должен требоваться только для исключений, а не для нормального потока импорта, обогащения и проверки.

---

## 1. Проблемы текущей модели данных

### 1.1. Проблемы модели Place

1. Нет единого data contract для места.
2. `address` представлен как одно текстовое поле без структуры.
3. Нет разделения между data fields и display fields.
4. `opening_hours` нельзя использовать напрямую без нормального парсера и модели.
5. `image_url` legacy поле живет параллельно с `place_images`.
6. `slug` глобально уникален, что приведет к коллизиям в разных городах.
7. Нет version/revision на месте.
8. Confidence представлен агрегатом, а не разбивкой по полям.
9. Мусорные POI фильтруются хрупко, без явной allowlist/blocklist системы.
10. Нет `geo_precision`.
11. Нет temporal-полей для сезонных мест.
12. Tags представлены простым массивом строк без canonical vocabulary.

### 1.2. Проблемы модели City

13. `places_count` может расходиться с реальным количеством мест.
14. Нет city-level data quality snapshot.
15. Координаты города могут расходиться между источниками.
16. Нет language metadata для города.
17. Нет timezone на уровне города.

### 1.3. Проблемы pipeline

18. Enrichment не идемпотентен на уровне отдельных полей.
19. Нет retry с backoff для внешних API.
20. Нет provenance данных на уровне поля.
21. Дедупликация недостаточна: нет geo-proximity + name similarity.
22. Pipeline недостаточно наблюдаем: нет нормальных метрик прогресса и причин отказов.

---

## 2. Риски масштабирования

### 2.1. Горизонт 10 городов

- Ручная операционная модель станет узким местом.
- Внешние API быстро упрутся в rate limits.
- Coverage/report запросы станут медленными без материализации.
- Коллизии slug станут регулярными.

### 2.2. Горизонт 100 городов

- PostgreSQL как task queue не масштабируется.
- Storage для фото станет отдельной инфраструктурной задачей.
- Public Overpass API не выдержит bulk-импорт.
- Ручная верификация не масштабируется.
- Появятся проблемы языков и локалей.
- Данные городов начнут устаревать неравномерно.

### 2.3. Горизонт 1000 городов

- Потребуется partitioning place-related таблиц по `city_id`.
- PostGIS-запросы должны всегда использовать `city_id` pre-filter.
- Внешние API могут стать существенной статьей расходов.
- Понадобится data governance и ownership model.
- AI-описания на множестве языков потребуют language quality validation.

---

## 3. Целевая архитектура Data Quality Layer

Data Quality Layer должен быть частью модели данных и поведения системы, а не отдельным отчетом.

### 3.1. Field Level

Каждое значимое поле должно иметь:

- source;
- confidence;
- obtained_at;
- is_manually_overridden;
- freshness_status.

Хранение: `place_field_provenance`.

### 3.2. Place Level

На уровне места хранятся агрегированные метрики:

- completeness_score;
- confidence_score;
- freshness_score;
- quality_tier: gold / silver / bronze / draft / rejected.

Хранение: денормализовано в `places` + история в `quality_score_history`.

### 3.3. City Level

На уровне города нужен материализованный снапшот:

- coverage metrics;
- readiness_score;
- quality_distribution;
- freshness metrics.

Хранение: `city_quality_snapshots`.

### 3.4. Архитектурные компоненты

- Quality Rules Engine.
- Quality Gate.
- Freshness Monitor.
- Confidence Resolver.

---

## 4. Модель качества места

### 4.1. Place Quality Score

#### Completeness Score — 0–40

Обязательные поля:

- coordinates: +10, отсутствие делает место невалидным;
- title: +8, отсутствие делает место невалидным;
- canonical category: +8, отсутствие делает место невалидным;
- city_id: обязательное поле, не участвует в score.

Важные поля:

- full address: +6;
- approximate address: +3;
- verified opening hours: +5;
- estimated opening hours: +3;
- visit_duration_minutes: +3.

#### Photo Score — 0–25

- exact place photo из Wikidata/Commons: +25;
- verified `og:image`: +20;
- unverified `og:image`: +15;
- area photo: +8;
- category placeholder: +2;
- no photo: 0.

#### Description Score — 0–15

- manual editorial description: +15;
- verified source / Wikipedia extract: +12;
- AI-generated reviewed: +10;
- AI-generated unreviewed: +6;
- template description: +1;
- no description: 0.

#### Confidence Score — 0–10

Weighted average по полям:

- address: 0.3;
- opening_hours: 0.3;
- category: 0.2;
- photo: 0.2.

#### Freshness Score — 0–10

- verified < 3 месяцев: +10;
- 3–6 месяцев: +8;
- 6–12 месяцев: +5;
- 12–18 месяцев: +2;
- > 18 месяцев: 0;
- never verified, only imported: +3.

### 4.2. Quality Tiers

| Tier | Score | Поведение |
|---|---:|---|
| Gold | 85–100 | В маршрутах без ограничений, в каталоге первым. |
| Silver | 65–84 | В маршрутах и каталоге. |
| Bronze | 40–64 | В маршрутах только если нет Gold/Silver альтернатив, в каталоге с пометкой. |
| Draft | 20–39 | Не используется в маршрутах, требует проверки. |
| Rejected | 0–19 | Скрыто от пользователей, только admin. |

### 4.3. Специальные флаги

- `is_duplicate_suspected` — понижает tier на один уровень.
- `is_spam_poi` — forced rejected.
- `user_rejection_count > 3` — forced draft.
- `opening_hours_conflict_detected` — penalty -10.

---

## 5. Модель качества города

### 5.1. City Quality Snapshot

Coverage metrics:

- total_places_imported;
- total_places_active;
- total_places_route_eligible;
- spam_poi_count;
- spam_poi_pct;
- photo coverage;
- address coverage;
- description coverage;
- hours coverage;
- coordinates precision coverage.

Quality distribution:

- gold_pct;
- silver_pct;
- bronze_pct;
- draft_pct;
- rejected_pct.

Freshness:

- avg_data_age_days;
- stale_places_pct;
- never_verified_pct.

### 5.2. City Readiness Score

Формула:

- exact photo coverage × 0.20;
- full address coverage × 0.20;
- any hours coverage × 0.15;
- any description coverage × 0.15;
- gold + silver share × 0.15;
- 100 - spam_poi_pct × 0.10;
- 100 - stale_places_pct × 0.05.

Penalties:

- -20 если spam_poi_pct > 15%;
- -15 если gold + silver < 30%;
- -10 если full address < 40%;
- -10 если hours_any < 30%.

### 5.3. Publication Thresholds

Минимум для публикации:

- readiness_score >= 60;
- address_any_pct >= 60;
- any_photo_pct >= 70;
- spam_poi_pct <= 10;
- total_places_route_eligible >= 20.

Рекомендованный уровень:

- readiness_score >= 75;
- exact photo coverage >= 40;
- full address coverage >= 65;
- hours_any >= 50.

### 5.4. Дополнительные атрибуты City

- timezone;
- primary_language;
- secondary_languages;
- osm_relation_id;
- last_import_at;
- next_import_at;
- data_owner;
- population_tier.

---

## 6. Lifecycle места

### 6.1. State Machine

Состояния:

- raw_imported;
- normalizing;
- normalized;
- enriching;
- enrichment_partial;
- enriched;
- ready_for_review;
- needs_data_improvement;
- active;
- needs_recheck;
- archived;
- rejected.

### 6.2. Автоматические переходы

- raw_imported → normalizing;
- normalizing → normalized;
- normalizing → rejected;
- normalized → enriching;
- enriching → enriched;
- enriching → enrichment_partial;
- enriched → ready_for_review;
- ready_for_review → active, если score >= silver;
- active → needs_recheck по freshness monitor;
- needs_recheck → enriching.

### 6.3. Ручные переходы

- needs_data_improvement → enriching;
- ready_for_review → active;
- ready_for_review → rejected;
- rejected → normalized;
- active → archived;
- archived → active;
- любое состояние → rejected.

### 6.4. place_state_transitions

Поля:

- id;
- place_id;
- from_state;
- to_state;
- triggered_by;
- trigger_reason;
- triggered_at;
- metadata.

---

## 7. Confidence System

### 7.1. Принцип

Confidence должен храниться на уровне поля, а не только на уровне места.

### 7.2. Источники confidence

| Источник | Поле | Confidence |
|---|---|---:|
| Ручная верификация | любое | 0.95–1.00 |
| Официальный сайт schema.org | hours, phone, url | 0.85–0.90 |
| Wikidata P18 | image | 0.90–0.95 |
| Wikimedia Commons depicts | image | 0.85–0.90 |
| OSM addr:* complete | address | 0.80–0.85 |
| Wikipedia extract | description | 0.80–0.85 |
| Google Places API | hours, phone, url | 0.80–0.85 |
| OSM addr:* partial | address | 0.65–0.75 |
| Geoapify reverse geocoding | address | 0.65–0.75 |
| Nominatim reverse geocoding | address | 0.60–0.70 |
| verified og:image | image | 0.65–0.75 |
| Mapillary area photo | image | 0.45–0.55 |
| AI-generated description reviewed | description | 0.60–0.70 |
| AI-generated description unreviewed | description | 0.40–0.55 |
| estimated default hours | hours | 0.20–0.30 |

### 7.3. Confidence Levels

- High Confidence >= 0.80.
- Medium Confidence 0.50–0.79.
- Low Confidence < 0.50.

### 7.4. Conflict resolution

- Если новый source_confidence выше текущего на 0.15+, обновить значение.
- Если разница в пределах 0.15, сохранить текущее и логировать конфликт.
- Если `is_manually_overridden = true`, не обновлять автоматически.
- Если оба источника > 0.75 и значения разные, добавить в conflict review queue.

---

## 8. Freshness System

### 8.1. Принцип

Разные поля устаревают с разной скоростью.

### 8.2. Freshness интервалы

| Поле | Fresh | Aging | Stale | Expired |
|---|---|---|---|---|
| coordinates | 2 года | 2–5 лет | 5–10 лет | 10+ лет |
| address | 1 год | 1–2 года | 2–4 года | 4+ лет |
| opening_hours verified | 3 месяца | 3–6 мес | 6–12 мес | 12+ мес |
| opening_hours estimated | 1 месяц | 1–3 мес | 3–6 мес | 6+ мес |
| phone | 6 месяцев | 6–12 мес | 1–2 года | 2+ лет |
| website | 6 месяцев | 6–12 мес | 1–2 года | 2+ лет |
| image exact_place | 1 год | 1–3 года | 3–5 лет | 5+ лет |
| image area_photo | 6 месяцев | 6–18 мес | 18–36 мес | 3+ лет |
| description manual | 1 год | 1–2 года | 2–4 года | 4+ лет |
| description AI | 6 месяцев | 6–12 мес | 1–2 года | 2+ лет |
| category | 2 года | 2–4 года | 4+ лет | — |
| tags | 1 год | 1–2 года | 2–4 года | 4+ лет |

### 8.3. Freshness Score

Weighted average:

- opening_hours × 0.35;
- address × 0.25;
- image × 0.20;
- phone/website × 0.10;
- description × 0.10.

### 8.4. Действия

- Aging: enrichment background queue, low priority.
- Stale: enrichment queue, medium priority, снизить confidence × 0.8.
- Expired: verification queue, high priority, downgrade tier.

### 8.5. Freshness Monitor

Ежедневный запуск в 04:00:

1. Найти stale/expired поля.
2. Приоритизировать gold и пользовательски активные места.
3. Добавить batch по 500 в enrichment retry queue.
4. Critical expired поля отправить в manual review queue.
5. Обновить city_quality_snapshots.

---

## 9. Автоматическое добавление города

### 9.1. Фаза 0 — City Discovery

Admin вводит название города на кириллице.

Система:

- ищет город через Nominatim;
- получает boundary/bbox;
- определяет timezone;
- определяет языки;
- определяет population tier;
- создает `city_enrichment_run`.

### 9.2. Фаза 1 — OSM Import

- Overpass query по allowlist POI types.
- Staging import в `place_import_staging`.
- Normalization.
- Spam detection.
- Deduplication.
- Insert в `places`.

### 9.3. Фаза 2 — Parallel Enrichment

Workers:

- Address Enrichment;
- Photo Enrichment;
- Hours + Contact Enrichment;
- Description Generation;
- Category + Tag Refinement.

### 9.4. Фаза 3 — Quality Calculation

- Пересчитать score мест.
- Назначить quality_tier.
- Рассчитать city readiness snapshot.
- Сгенерировать coverage report.

### 9.5. Фаза 4 — Auto-publishing Gate

- Если readiness >= threshold, bronze+ публикуются автоматически.
- Draft уходит в review queue.
- Rejected остается только в admin.
- Если readiness ниже threshold, город требует ручной работы.

### 9.6. Фаза 5 — Verification Queue

Приоритеты:

1. Conflicting data.
2. Score 40–64.
3. Топ-50 мест города.
4. Места без фото.
5. Suspected duplicates.

### 9.7. Orchestrator

Task graph:

```text
city_discovery
  ↓
osm_import
  ↓
normalization + dedup
  ↓
addresses / photos / hours / descriptions / tags
  ↓
quality_calculation
  ↓
auto_publish_gate
  ↓
verification_queue_generation
  ↓
notify_admin
```

Технические компоненты:

- PostgreSQL для state;
- ARQ + Redis или Celery для task execution;
- Admin UI polling или WebSocket;
- exponential backoff;
- idempotency на уровне задач.

---

## 10. Roadmap Этапа 1

### P0. Фундамент

Срок: 1–2 недели.

1. Исправить slug uniqueness на `(city_id, slug)`.
2. Добавить timezone и language в City.
3. Создать `place_field_provenance`.
4. Создать `city_enrichment_runs` и `enrichment_tasks`.
5. Ввести canonical tag vocabulary.
6. Исправить spam POI allowlist/blocklist.

### P1. Place State Machine

Срок: 2–3 недели.

1. Реализовать lifecycle status для места.
2. Создать `place_state_transitions`.
3. Переработать Quality Score.
4. Ввести Quality Tier.
5. Включить Quality Gate для маршрутов.
6. Создать материализованный City Quality Snapshot.
7. Переработать Verification Queue.

### P2. Enrichment Orchestrator

Срок: 3–5 недель.

1. Parallel enrichment workers.
2. Rate Limit Manager.
3. Retry system.
4. Admin кнопка «Обогатить город».
5. Progress UI в admin.
6. Полный provenance UI для admin.

### P3. Автоматическое добавление города

Срок: 5–8 недель.

1. City Discovery.
2. Полный автоматический pipeline.
3. Freshness Monitor.
4. Conflict Detection.
5. Conflict Resolution UI.
6. Auto-publish Gate.

---

## 11. Что не делать в Этапе 1

- Не начинать крупные улучшения Route Engine до завершения P0.
- Не строить собственный Overpass instance на этом этапе.
- Не внедрять ML ranking.
- Не масштабироваться на 100 городов до стабильности на 10.
- Не строить mobile app.
- Не ломать существующие маршруты во время P0–P1.

---

## 12. Критерии готовности Этапа 1

### 12.1. Технические критерии

- `slug` уникален внутри города.
- `place_field_provenance` заполнен для 100% мест.
- Quality tier назначен для 100% мест.
- City readiness score считается из снапшота, не live-запросами.
- Enrichment запускается из UI без SSH.

### 12.2. Качественные критерии

- address coverage > 70% для всех published городов.
- any_photo coverage > 80% для всех published городов.
- spam_poi_pct < 5% для всех published городов.
- Новый город добавляется за < 2 часа автоматики + 1 час ревью.
- 0 мест попадает в маршруты без coordinates и без category.
