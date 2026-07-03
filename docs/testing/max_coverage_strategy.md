# City GO · Maximum Autotest Coverage Strategy

## Цель

CI должен сообщать о сломанном продукте раньше ручной проверки и раньше production deploy. Production smoke не должен быть первым местом, где обнаруживаются продуктовые дефекты; каждый smoke-check обязан иметь regression/predeploy equivalent.

Тесты описывают целевое поведение платформы, а не текущее фактическое состояние кода. Если тест падает, сначала определяется причина: дефект продукта или дефект теста. Тест меняется только если он противоречит утверждённому продуктовому контракту, архитектурному решению или неверно проверяет реализацию. Если тест правильно описывает, как платформа должна работать, чинится функционал.

## Triage policy для красного теста

1. Прочитать assertion и определить проверяемый продуктовый контракт.
2. Сравнить контракт с текущими требованиями City GO.
3. Если контракт правильный, тест остаётся красным до фикса продукта.
4. Если тест проверяет внутреннюю деталь вместо пользовательского/публичного поведения, тест переписывается на целевой контракт.
5. Если продуктовая логика спорная, фиксируется решение в документации и только после этого меняется код или тест.
6. Запрещено “подгонять” тест под кривой функционал ради зелёного CI.
7. Для багов маршрутизации, качества данных, публичного API, админки и smoke parity приоритет по умолчанию — чинить платформу, а не ослаблять тест.

Примеры:

- Маршрут строится из 1 точки при достаточном количестве валидных мест — баг route builder, тест должен падать.
- В маршрут попала аптека, банк, остановка или OSM placeholder — баг eligibility/retrieval/output gate, тест должен падать.
- Public API отдаёт raw internal code в user-facing поле — баг API contract, тест должен падать.
- Тест ожидает сырой внутренний alias категории, хотя продуктовый контракт требует каноническую категорию — баг теста.
- Тест ожидает запрет bronze quality, но утверждённая политика разрешает bronze для recall в городах с неполными данными — сначала пересмотреть продуктовую политику, потом менять код или тест.

## Обязательные уровни покрытия

1. Unit tests: чистые функции, политики, нормализация, scoring, eligibility, warnings.
2. Service tests: route builder, route edit, city counters, admin aggregation, publication/reconciliation.
3. API contract tests: public route API, admin API, city API, taxonomy API, stable JSON shape.
4. Frontend component tests: route widgets, admin widgets, forms, search, crash boundaries.
5. Smoke-equivalence tests: все проверки scripts/production_smoke.py должны дублироваться локально.
6. Production smoke: только короткое подтверждение деплоя и live env, не уникальная продуктовая валидация.

## Техники тест-дизайна

### Equivalence Partitioning

Классы данных должны проверяться матрицами, а не единичными примерами:

- allowed route categories;
- hard-excluded categories;
- public warning types;
- raw/internal warning codes;
- visible catalog places;
- hidden/unpublished/inactive places;
- admin endpoint response shapes.

### Boundary Value Analysis

Обязательные границы:

- time_budget_minutes: 15, 60, 74, 75, 120, 240, 1440;
- route points: 0, 1, 2, expected_min - 1, expected_min, MAX_ROUTE_POINTS, MAX_ROUTE_POINTS + 1;
- slot min_count/max_count: 1, max < min, sum > max allowed;
- admin pagination: offset 0, limit 1, limit max;
- empty/non-empty city quality datasets.

### Decision Tables

Должны быть покрыты комбинации:

- active/published/visible/catalog/route_eligible;
- canonical_category vs display category;
- city active/published flags;
- quality tier, spam, duplicate, expired field;
- status/quality_status/partial_reason/warnings for short or overflowing routes.

### State Transition Testing

Маршруты и сессии должны проверяться как состояния:

- ready -> partial_route -> no_route;
- preview -> preview_failed;
- planned -> active -> paused -> active -> completed;
- active -> abandoned;
- invalid transition -> 422/conflict.

### Negative Testing

Обязательные плохие данные:

- route_builder_v2_*;
- unknown_internal_code;
- SECRET_TOKEN, bearer token, database URL, traceback;
- Node 123, Way 123, Unnamed POI, OSM node;
- pharmacy, bank, atm, bus_stop, stop, medical, service, utility;
- broken admin filters and missing JSON keys.

### Contract Testing

Публичный API не должен отдавать internal implementation details в user-facing fields:

- warnings;
- user_warnings;
- user_warnings.type;
- user_warnings.user_message;
- partial_reason;
- user_explanation;
- explanation;
- route_builder_v2 public explanation.

Production smoke and local contract tests must report the exact JSON path for raw code leaks, not only a generic payload failure.

### Admin Backlog Breakdown

Admin overview tests must not stop at card shape. Large queues require decomposition
tests:

- queue total vs unique place count;
- total problem signals vs unique places;
- reason-level counts and sample endpoint totals;
- auto/manual split for review and verification queues;
- overlap counts between manual review, verification, content gaps and route blockers;
- Russian operator copy with no raw snake_case reason codes in the UI.

### Pairwise / Combinatorial Testing

Для route request нужно покрывать не полный декартов взрыв, а pairwise-набор:

- build_mode;
- start_source;
- city_id present/missing;
- interests empty/non-empty;
- selected_place_ids empty/non-empty;
- route_slots empty/valid/invalid;
- time_budget short/normal/long.

### Error Guessing from History

Каждый найденный пользователем дефект должен становиться regression test:

- 400/500 в админке;
- белая страница при вводе букв;
- аптеки/остановки в маршруте;
- OSM placeholders в маршруте;
- raw technical codes in public payload;
- /api path mismatch;
- city selector counters dropping after route eligibility changes;
- duplicate city places/reporting;
- readiness false zero.

## Definition of Done for new functionality

Новая функциональность не считается готовой, если нет:

1. Positive path test.
2. Negative path test.
3. Boundary test.
4. Public API contract test, если есть API.
5. UI crash/render test, если есть UI.
6. Admin/API shape test, если функциональность видна в админке.
7. Smoke-equivalence test, если сценарий попадает в production smoke.
8. Regression test for the exact bug, если это bugfix.

## Coverage targets

- backend overall: 90%+;
- backend platform: 90%+;
- backend admin: 90%+;
- changed backend files: 90%+;
- frontend changed components: 90%+ meaningful branch/behavioral coverage;
- all production smoke assertions: 100% local regression equivalent.

Line coverage не заменяет behavioral coverage. Цель — не только проценты, а невозможность пропустить критичный сломанный сценарий.
