# City Go — Data Foundation Architecture

Версия: 1.0  
Статус: Source of Truth  
Этап: Data Foundation  
Последнее обновление: 2026-06-18

Документ определяет архитектурные правила работы с данными в City Go. На него нужно опираться при доработках импорта, обогащения, маршрутов, качества данных, городов, категорий и карточек мест.

---

## 1. Назначение документа

City Go зависит от качества каталога. Если места неполные, неточные или мусорные, маршрутный движок и AI-слой будут выдавать плохой результат независимо от качества алгоритмов.

Этот документ фиксирует:

- что считается валидным местом;
- что считается готовым городом;
- какие места допускаются в маршруты;
- как считается качество места;
- как считается качество города;
- как работают confidence и freshness;
- как должен работать импорт и enrichment;
- что нужно реализовать в первую очередь.

---

## 2. Главные принципы

### 2.1. Data Contract важнее pipeline

Pipeline сам по себе не решает проблему качества. Нужен явный контракт: какие поля обязательны, какие поля важны, какие поля влияют на публикацию и маршруты.

### 2.2. Quality Score должен быть gate, а не декоративной метрикой

Если score считается, но не влияет на публикацию места, публикацию города или попадание места в маршрут, он бесполезен. Нужны quality gates.

### 2.3. Места низкого качества не должны попадать в маршруты

Пользователь не различает Gold, Silver и Bronze. Если в маршруте плохое место, виноват продукт. Поэтому в маршруты допускаются только Gold и Silver.

### 2.4. Ручная работа допустима только для исключений

На масштабе 100+ городов ручная проверка каждого места невозможна. Система должна автоматически импортировать, обогащать, оценивать, публиковать или отправлять в очередь проверки.

### 2.5. Title-based filtering запрещен

Фильтрация аптек, остановок и другого мусора через поиск слов в названии запрещена. Фильтрация должна происходить через категории, OSM tags, allowlist/blocklist и route eligibility contract.

---

## 3. Цели этапа Data Foundation

Главная цель: пользователь должен доверять данным.

Этап считается успешным, если:

- места имеют координаты;
- места имеют категории;
- места имеют адреса;
- места имеют фото;
- места имеют описание;
- места имеют режим работы там, где это применимо;
- маршруты строятся только из качественных мест;
- мусорные POI не попадают в каталог и маршруты;
- новый город можно добавить из админки;
- качество города измеряется объективными метриками;
- данные имеют provenance, confidence и freshness.

---

## 4. Data Contract

### 4.1. Place

Минимально валидное место обязано иметь:

- `id`;
- `city_id`;
- `title`;
- `slug`;
- `latitude`;
- `longitude`;
- `canonical_category`;
- `lifecycle_status`.

Если отсутствует `title`, координаты или `canonical_category`, место считается невалидным и не может участвовать в маршрутах.

### 4.2. Важные поля Place

Эти поля не всегда являются обязательными для хранения, но влияют на качество и публикацию:

- `address`;
- `opening_hours`;
- `description`;
- `visit_duration_minutes`;
- `tags`;
- `photo`;
- `website`;
- `phone`;
- `source_url`.

### 4.3. Дополнительные поля Place

Эти поля нужны для будущих сценариев:

- `email`;
- `social_links`;
- `ticket_price`;
- `price_level`;
- `accessibility`;
- `dog_friendly`;
- `seasonal_start`;
- `seasonal_end`;
- `is_seasonal`;
- `geo_precision`.

### 4.4. City

Город обязан иметь:

- `id`;
- `name`;
- `slug`;
- `timezone`;
- `primary_language`;
- `center_latitude`;
- `center_longitude`;
- `osm_relation_id` или другой надежный boundary identifier;
- `boundary` или `bbox`.

Дополнительные поля:

- `secondary_languages`;
- `last_import_at`;
- `next_import_at`;
- `population_tier`;
- `expected_places_count`.

---

## 5. Canonical Category Registry

Все внешние категории и OSM tags должны маппиться в канонический список категорий.

### 5.1. Разрешенные категории

Базовый список:

- `museum`;
- `park`;
- `viewpoint`;
- `architecture`;
- `beach`;
- `embankment`;
- `nature`;
- `restaurant`;
- `cafe`;
- `bar`;
- `theatre`;
- `gallery`;
- `shopping`;
- `hotel`;
- `landmark`;
- `entertainment`;
- `historical_site`;
- `family`;
- `sport`;
- `attraction`.

### 5.2. Правила категорий

- Категории должны быть управляемыми из админки.
- Категории должны иметь флаг `is_route_eligible`.
- Категории должны иметь флаг `is_catalog_visible`.
- Категории должны иметь флаг `is_default_enabled`.
- Маппинг OSM tags должен быть явным.
- Нельзя определять категорию по названию места.

---

## 6. Route Eligibility Contract

Место может попасть в маршрут только если выполняются все условия:

- `lifecycle_status = active`;
- `quality_tier IN ('gold', 'silver')`;
- `is_route_eligible = true`;
- координаты присутствуют;
- `canonical_category` присутствует;
- место не является spam;
- место не является duplicate;
- место не archived;
- категория разрешена для маршрутов;
- город опубликован или доступен в текущем окружении.

Bronze, Draft и Rejected в маршруты не попадают.

Если после фильтрации маршрут становится слишком коротким, система должна вернуть честное предупреждение, а не добавлять некачественные места.

---

## 7. Spam POI Policy

### 7.1. По умолчанию запрещены

- `pharmacy`;
- `atm`;
- `fuel`;
- `parking`;
- `bus_stop`;
- `public_toilet`;
- `vending_machine`;
- `bench`;
- `waste_basket`;
- `charging_station`;
- `post_box`.

### 7.2. Исключения

Некоторые типы могут быть разрешены только как часть отдельного сценария, но не как туристические точки маршрута по умолчанию.

Например:

- аптеки — полезный слой карты, но не туристический маршрут;
- парковки — инфраструктурный слой, но не маршрут;
- остановки — транспортный слой, но не маршрут.

### 7.3. Запреты

Запрещено:

- фильтровать мусорные POI через `title ilike`;
- скрывать мусор только на frontend;
- оставлять route eligibility на усмотрение UI;
- смешивать туристические места и инфраструктурные POI в одной логике.

---

## 8. Place Lifecycle

### 8.1. Состояния

- `raw_imported` — место импортировано, но не нормализовано;
- `normalizing` — идет нормализация;
- `normalized` — нормализация завершена;
- `enriching` — идет обогащение;
- `enrichment_partial` — обогащение выполнено частично;
- `enriched` — обогащение завершено;
- `ready_for_review` — готово к проверке;
- `needs_data_improvement` — данных недостаточно;
- `active` — опубликовано;
- `needs_recheck` — требуется перепроверка;
- `archived` — архивировано;
- `rejected` — отклонено.

### 8.2. Автоматические переходы

- `raw_imported → normalizing`;
- `normalizing → normalized`;
- `normalizing → rejected`, если spam или дубль;
- `normalized → enriching`;
- `enriching → enriched`;
- `enriching → enrichment_partial`;
- `enriched → ready_for_review`;
- `ready_for_review → active`, если score достаточный;
- `active → needs_recheck`, если данные устарели;
- `needs_recheck → enriching`.

### 8.3. Ручные переходы

- `ready_for_review → active`;
- `ready_for_review → rejected`;
- `needs_data_improvement → enriching`;
- `rejected → normalized`;
- `active → archived`;
- `archived → active`;
- любое состояние → `rejected`.

### 8.4. История переходов

Нужна таблица `place_state_transitions`:

- `id`;
- `place_id`;
- `from_state`;
- `to_state`;
- `triggered_by`;
- `trigger_reason`;
- `triggered_at`;
- `metadata`.

---

## 9. Data Quality Layer

Data Quality Layer состоит из трех уровней.

### 9.1. Field Level

Для каждого значимого поля хранится:

- `source`;
- `confidence`;
- `obtained_at`;
- `freshness_status`;
- `is_manually_overridden`;
- `raw_value`;
- `normalized_value`.

Таблица: `place_field_provenance`.

### 9.2. Place Level

На уровне места хранятся агрегированные метрики:

- `completeness_score`;
- `photo_score`;
- `description_score`;
- `confidence_score`;
- `freshness_score`;
- `quality_score`;
- `quality_tier`.

### 9.3. City Level

На уровне города хранятся материализованные метрики:

- `readiness_score`;
- `coverage_score`;
- `quality_distribution`;
- `freshness_distribution`;
- `spam_poi_pct`;
- `route_eligible_count`.

Таблица: `city_quality_snapshots`.

---

## 10. Place Quality Model

### 10.1. Quality Score

`quality_score` считается по шкале 0–100.

Состав:

- completeness: 40;
- photo: 25;
- description: 15;
- confidence: 10;
- freshness: 10.

### 10.2. Completeness Score

Максимум: 40.

Обязательные поля:

- coordinates: +10, отсутствие делает место невалидным;
- title: +8, отсутствие делает место невалидным;
- canonical category: +8, отсутствие делает место невалидным;
- city_id: обязательно, не участвует в score.

Важные поля:

- full address: +6;
- approximate address: +3;
- verified opening hours: +5;
- estimated opening hours: +3;
- visit_duration_minutes: +3.

### 10.3. Photo Score

Максимум: 25.

- exact place photo from Wikidata / Commons: +25;
- verified og:image: +20;
- unverified og:image: +15;
- area photo: +8;
- category placeholder: +2;
- no photo: 0.

### 10.4. Description Score

Максимум: 15.

- manual editorial description: +15;
- verified source / Wikipedia extract: +12;
- AI-generated reviewed: +10;
- AI-generated unreviewed: +6;
- template description: +1;
- no description: 0.

### 10.5. Confidence Score

Максимум: 10.

Weighted average:

- address confidence × 0.30;
- opening_hours confidence × 0.30;
- category confidence × 0.20;
- photo confidence × 0.20.

### 10.6. Freshness Score

Максимум: 10.

- verified < 3 месяцев: +10;
- 3–6 месяцев: +8;
- 6–12 месяцев: +5;
- 12–18 месяцев: +2;
- > 18 месяцев: 0;
- never verified, only imported: +3.

---

## 11. Quality Tiers

### 11.1. Gold

Score: 85–100.

Поведение:

- участвует в маршрутах;
- показывается в каталоге;
- приоритетно ранжируется;
- не требует предупреждений пользователю.

### 11.2. Silver

Score: 65–84.

Поведение:

- участвует в маршрутах;
- показывается в каталоге;
- может иметь мягкие предупреждения для отдельных полей, например часы работы требуют уточнения.

### 11.3. Bronze

Score: 40–64.

Поведение:

- показывается в каталоге;
- не участвует в маршрутах;
- помечается как место с данными, которые уточняются.

### 11.4. Draft

Score: 20–39.

Поведение:

- скрыто от пользователей;
- находится в очереди проверки или дообогащения.

### 11.5. Rejected

Score: 0–19.

Поведение:

- скрыто от пользователей;
- доступно только в админке;
- требует ручного решения для восстановления.

### 11.6. Принудительные правила

- `is_spam_poi = true` → forced rejected;
- `is_duplicate_suspected = true` → downgrade на один tier;
- `opening_hours_conflict_detected = true` → penalty -10;
- `critical_field_expired = true` → убрать из маршрутов до перепроверки.

---

## 12. City Quality Model

### 12.1. City Quality Snapshot

Снапшот должен считаться автоматически и храниться материализованно.

Метрики:

- `total_places_imported`;
- `total_places_active`;
- `total_places_route_eligible`;
- `spam_poi_count`;
- `spam_poi_pct`;
- `photo_coverage_pct`;
- `any_photo_pct`;
- `address_full_pct`;
- `address_any_pct`;
- `description_any_pct`;
- `hours_any_pct`;
- `coordinates_precise_pct`;
- `gold_pct`;
- `silver_pct`;
- `bronze_pct`;
- `draft_pct`;
- `rejected_pct`;
- `avg_data_age_days`;
- `stale_places_pct`;
- `never_verified_pct`.

### 12.2. City Readiness Score

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

### 12.3. Статусы города

- `ready`: readiness_score >= 75;
- `needs_review`: readiness_score 60–74;
- `not_ready`: readiness_score < 60.

### 12.4. Publication Thresholds

Город можно публиковать только если:

- readiness_score >= 75;
- address_any_pct >= 70;
- any_photo_pct >= 80;
- spam_poi_pct <= 5;
- total_places_route_eligible >= 20.

Если readiness_score 60–74, город не публикуется автоматически и уходит в ручную проверку.

---

## 13. Confidence Model

### 13.1. Принцип

Confidence хранится на уровне поля, а не только на уровне места.

### 13.2. Confidence Levels

High Confidence: 0.80+.

Источники:

- ручная проверка;
- официальный сайт;
- Wikidata;
- Wikimedia Commons;
- полный OSM адрес;
- структурированные verified данные.

Medium Confidence: 0.50–0.79.

Источники:

- Geoapify;
- Nominatim;
- Wikipedia extract;
- AI-generated reviewed;
- verified og:image.

Low Confidence: <0.50.

Источники:

- AI-generated unreviewed;
- estimated default hours;
- category placeholder;
- approximate address;
- слабые inferred данные.

### 13.3. Conflict Resolution

При обновлении поля:

- если новое confidence выше текущего на 0.15+, обновить значение;
- если разница в пределах 0.15, сохранить текущее и логировать конфликт;
- если `is_manually_overridden = true`, не обновлять автоматически;
- если два источника имеют confidence > 0.75 и разные значения, отправить в conflict review queue.

---

## 14. Freshness Model

### 14.1. Принцип

Разные поля устаревают с разной скоростью.

Координаты меняются редко. Часы работы меняются часто. Фото и описание меняются средне.

### 14.2. Freshness Status

- `fresh`;
- `aging`;
- `stale`;
- `expired`.

### 14.3. Интервалы

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

### 14.4. Действия

- `aging`: добавить в enrichment background queue с низким приоритетом;
- `stale`: добавить в enrichment queue со средним приоритетом, снизить confidence × 0.8;
- `expired`: добавить в verification queue с высоким приоритетом, downgrade tier;
- expired critical field: убрать место из маршрутов до перепроверки.

### 14.5. Freshness Monitor

Запуск ежедневно в 04:00.

Алгоритм:

1. Найти места с stale/expired полями.
2. Приоритизировать Gold, Silver и пользовательски активные места.
3. Добавить batch по 500 в enrichment retry queue.
4. Critical expired поля отправить в manual review queue.
5. Обновить `city_quality_snapshots`.

---

## 15. Import & Enrichment Architecture

### 15.1. Основной pipeline

1. Discovery.
2. Import.
3. Normalize.
4. Deduplicate.
5. Enrich.
6. Quality Calculation.
7. Publish Gate.
8. Verification Queue.

### 15.2. Staging

Raw external data нельзя сразу писать в `places` как готовые данные.

Нужен staging слой:

- `place_import_staging`;
- raw source payload;
- source type;
- import run id;
- normalized candidate data;
- import errors.

### 15.3. Deduplication

Дедупликация должна использовать:

- source id;
- source url;
- geo proximity;
- name similarity;
- category similarity.

Node и way из OSM могут описывать один физический объект и не должны становиться дублями.

### 15.4. Enrichment Workers

Нужны отдельные worker-типы:

- Address Enrichment;
- Photo Enrichment;
- Hours + Contact Enrichment;
- Description Generation;
- Category + Tag Refinement.

### 15.5. Rate Limiting

Все внешние API должны проходить через общий rate limit manager.

Особенно важно для:

- Nominatim;
- Overpass;
- Wikimedia;
- Wikipedia;
- Geoapify;
- Google Places, если будет подключен.

### 15.6. Retry

Нужна retry-система:

- exponential backoff;
- тип ошибки;
- количество попыток;
- next_retry_at;
- last_error;
- terminal failure.

---

## 16. Automatic City Onboarding

### 16.1. Вход

Администратор вводит название города на кириллице.

Например:

`Алматы`

### 16.2. City Discovery

Система должна:

- найти город;
- если есть неоднозначность, показать варианты;
- получить bbox/boundary;
- получить timezone;
- определить primary_language;
- определить secondary_languages;
- определить population_tier;
- создать `city_enrichment_run`.

### 16.3. OSM Import

Система должна:

- построить Overpass query по allowlist POI types;
- исключить spam POI;
- импортировать raw данные в staging;
- нормализовать;
- дедуплицировать;
- создать места в статусе `raw_imported` / `normalized`.

### 16.4. Parallel Enrichment

Система запускает workers:

- addresses;
- photos;
- hours;
- descriptions;
- tags.

### 16.5. Quality Calculation

После enrichment:

- пересчитать score мест;
- назначить quality_tier;
- рассчитать city readiness;
- создать coverage report.

### 16.6. Publish Gate

Если город проходит thresholds:

- Gold/Silver места публикуются;
- Bronze показывается в каталоге, но не в маршрутах;
- Draft уходит в review queue;
- Rejected остается только в admin.

Если город не проходит thresholds:

- город получает статус `needs_review` или `not_ready`;
- публикация блокируется;
- admin получает отчет.

---

## 17. Admin Requirements

Админка должна поддерживать:

- запуск импорта города;
- запуск переобогащения города;
- запуск переобогащения отдельного места;
- просмотр city readiness;
- просмотр качества мест;
- просмотр provenance по каждому полю;
- просмотр confidence по каждому полю;
- просмотр freshness по каждому полю;
- review queue;
- conflict review queue;
- управление категориями;
- управление spam policy;
- управление route eligibility;
- массовые действия по местам;
- отчет после добавления города.

---

## 18. Technical Requirements

### 18.1. Таблицы

Нужно реализовать или проверить наличие:

- `place_field_provenance`;
- `city_quality_snapshots`;
- `city_enrichment_runs`;
- `enrichment_tasks`;
- `place_state_transitions`;
- `place_import_staging`;
- `canonical_categories`;
- `osm_category_mappings`;
- `spam_poi_rules`;
- `quality_score_history`.

### 18.2. Поля Place

Нужно добавить или проверить:

- `canonical_category`;
- `lifecycle_status`;
- `quality_score`;
- `quality_tier`;
- `completeness_score`;
- `photo_score`;
- `description_score`;
- `confidence_score`;
- `freshness_score`;
- `is_route_eligible`;
- `is_spam_poi`;
- `is_duplicate_suspected`;
- `geo_precision`;
- `last_verified_at`.

### 18.3. Поля City

Нужно добавить или проверить:

- `timezone`;
- `primary_language`;
- `secondary_languages`;
- `osm_relation_id`;
- `boundary`;
- `bbox`;
- `readiness_score`;
- `quality_status`;
- `last_import_at`;
- `next_import_at`.

### 18.4. Ограничения

Нужно реализовать:

- slug unique per city: `(city_id, slug)`;
- запрет route eligibility без coordinates;
- запрет route eligibility без canonical_category;
- запрет route eligibility для Bronze/Draft/Rejected;
- защита manually overridden полей от автоперезаписи.

---

## 19. Roadmap реализации

### 19.1. P0 — Foundation

Цель: закрыть фундаментальные проблемы данных.

Работы:

1. Исправить slug uniqueness на `(city_id, slug)`.
2. Добавить timezone и language в City.
3. Создать `place_field_provenance`.
4. Создать `city_enrichment_runs` и `enrichment_tasks`.
5. Создать canonical category registry.
6. Создать OSM mapping для категорий.
7. Создать spam POI allowlist/blocklist.
8. Запретить title-based filtering.

### 19.2. P1 — Quality Layer

Цель: сделать качество данных исполняемым правилом.

Работы:

1. Реализовать lifecycle status.
2. Создать `place_state_transitions`.
3. Реализовать Quality Score.
4. Реализовать Quality Tier.
5. Реализовать Route Eligibility Contract.
6. Реализовать City Quality Snapshot.
7. Реализовать Verification Queue.

### 19.3. P2 — Enrichment Platform

Цель: сделать обогащение управляемым процессом.

Работы:

1. Реализовать enrichment workers.
2. Реализовать retry system.
3. Реализовать rate limit manager.
4. Реализовать orchestrator.
5. Добавить кнопку «Обогатить город».
6. Добавить progress UI.
7. Добавить provenance UI.

### 19.4. P3 — Automatic City Pipeline

Цель: добавить город через админку одной операцией.

Работы:

1. City Discovery.
2. Full import pipeline.
3. Parallel enrichment.
4. Freshness Monitor.
5. Conflict Detection.
6. Auto Publish Gate.
7. Report после добавления города.

---

## 20. Что не делать в Этапе 1

Не делать сейчас:

- partitioning;
- self-hosted Overpass;
- ML ranking;
- сложную recommendation system;
- mobile app;
- масштабирование на 100 городов до стабильности на 10;
- ачивки;
- квесты;
- монетизацию;
- сложную социальную механику.

Эти темы можно фиксировать как future work, но не включать в реализацию Data Foundation.

---

## 21. Definition of Done

Этап Data Foundation считается завершенным, если выполнены все условия:

### 21.1. Технические критерии

- `slug` уникален внутри города;
- `place_field_provenance` существует и заполняется;
- все места имеют `quality_tier`;
- все города имеют `readiness_score`;
- city readiness считается из snapshot, а не тяжелыми live-запросами;
- enrichment запускается из UI без SSH;
- route builder использует только Gold/Silver места;
- route builder не использует spam, duplicate, archived места;
- title-based filtering удален из route/data logic.

### 21.2. Качественные критерии

- address coverage > 70% для published городов;
- any_photo coverage > 80% для published городов;
- spam_poi_pct < 5% для published городов;
- total_places_route_eligible >= 20 для published города;
- 0 мест попадает в маршруты без coordinates;
- 0 мест попадает в маршруты без canonical_category;
- новый город добавляется через admin UI;
- новый город получает отчет качества после импорта;
- данные имеют confidence;
- данные имеют freshness;
- данные имеют provenance.

---

## 22. Главный порядок работ

Правильная последовательность:

1. Data Contract.
2. Category Registry.
3. Spam POI Policy.
4. Place Lifecycle.
5. Quality Tier.
6. Route Eligibility Contract.
7. City Readiness.
8. Enrichment Orchestrator.
9. Automatic City Onboarding.

Route Engine, карта и AI-персонализация должны опираться на этот фундамент, а не обходить его локальными костылями.
