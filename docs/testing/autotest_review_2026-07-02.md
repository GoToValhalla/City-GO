# CITY GO — Autotest Review 2026-07-02

Цель: зафиксировать проблемы покрытия и качества автотестов после серии регрессий в admin/publication/import/Telegram flows.

## Scope ревью

Проверены текущие источники:

- `.github/workflows/ci.yml`
- `frontend/package.json`
- `tests/conftest.py`
- `tests/test_public_catalog_e2e_regression.py`
- `tests/test_legacy_source_of_truth_contracts.py`
- публикационные invariants/docs
- legacy register/docs

## Главные выводы

### 1. CI не запускается автоматически из `ci.yml`

`Full Autotests` сейчас имеет только:

```yaml
on:
  workflow_dispatch:
```

Это означает, что workflow нельзя считать полноценным push/PR gate, если нет отдельного внешнего запуска. Для защиты main нужны явные triggers:

```yaml
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:
```

Риск: regression может попасть в main до запуска полного набора автотестов.

### 2. Frontend lint фактически не валит CI

В `frontend/package.json`:

```json
"lint": "eslint . || true"
```

В workflow отдельно проверяется `LINT_EXIT`, но из-за `|| true` он почти всегда будет `0`.

Риск: lint ошибки скрываются и попадают в зелёный frontend job.

Нужно заменить на:

```json
"lint": "eslint ."
```

### 3. Backend тестовая БД смешивает две модели схемы

В `tests/conftest.py` одновременно есть:

- session-level Alembic migration для `settings.database_url`;
- отдельная in-memory SQLite через `Base.metadata.create_all()` для fixtures.

Риск: тесты могут проходить на metadata schema, но ломаться на реальной migration schema, или наоборот. Это уже проявлялось в NOT NULL/FK ошибках.

Нужно привести к одному контракту:

- либо все backend integration tests используют Alembic-created DB;
- либо отдельные unit tests явно маркируются как metadata-only;
- migration/schema contract tests должны проверять NOT NULL, FK, unique constraints для критичных таблиц.

### 4. Fixtures по умолчанию создают слишком happy-path данные

`place_factory` по умолчанию создаёт место как опубликованное и видимое:

```python
is_active=True
is_published=True
is_visible_in_catalog=True
is_route_eligible=True
is_searchable=True
publication_status='published'
```

Риск: тесты не ловят, когда service случайно публикует или делает видимым место, потому что fixture уже published.

Нужно:

- оставить `place_factory` простым, но добавить отдельные explicit fixtures:
  - `published_place_factory`;
  - `draft_place_factory`;
  - `manual_review_place_factory`;
  - `auto_backlog_place_factory`;
  - `hidden_place_factory`;
- в новых тестах запрещать неявную публикацию через default fixture для publication/admin flows.

### 5. Legacy source-of-truth confusion уже пойман отдельным guard

Добавлен guard:

```text
tests/test_legacy_source_of_truth_contracts.py
```

Он защищает кейс, где тесты/фиксы брали `PlaceChangeReview`, хотя active endpoint реально читает `ReviewQueueItem`.

Нужно расширить такой подход на другие legacy зоны:

- old `city_import_jobs` vs active `city_admin_import_jobs`;
- old `itinerary_*` vs active route builder flow;
- unregistered `telegram_bot/handlers/route.py` vs active registered routers.

### 6. Allure readable titles есть, но явное покрытие сценариев слабое

CI summary ранее показывал около 52% explicit Russian scenarios. Это значит, что часть тестов всё ещё технические, а не сценарные.

Нужно ввести правило:

- каждый regression по production incident должен иметь человекочитаемый сценарий;
- критичные admin/import/publication/Telegram tests должны иметь Russian scenario title через helper/decorator;
- summary должен подсвечивать не только процент, но и список тестов без readable title.

### 7. Performance/query-budget tests есть, но покрытие не системное

В проекте есть query budget checks для admin overview/coverage, но они не покрывают все high-risk paths:

- latest import job per city;
- Telegram moderation city list/next item;
- admin summaries with city table;
- auto backlog batch cursor processing;
- publication diagnostics/repair scripts.

Нужно добавить budget tests на эти paths и запретить N+1 по городам/местам.

### 8. Production health tests недостаточны

`/ready` должен быть fast и не зависеть от тяжёлых admin summaries. Это было заявлено как invariant, но нужно отдельное покрытие:

- `/ready` no DB-heavy query;
- `/ready` survives admin summary failures;
- worker startup smoke imports all registered routers/services;
- deploy/build smoke must fail on missing imports before pushing images.

## Приоритетный план фиксов автотестов

### P0 — немедленно

1. Включить automatic CI triggers для `push`/`pull_request`, если это не покрыто другим workflow.
2. Убрать `|| true` из frontend lint.
3. Добавить guard tests:
   - active admin import status не использует `city_import_jobs`;
   - active route endpoint не использует `services/itinerary_*`;
   - active Telegram dispatcher не регистрирует legacy `telegram_bot/handlers/route.py`.
4. Добавить endpoint chain guard для `/admin/place-change-reviews/*` уже сделано.

### P1 — publication/import/admin regression pack

1. Failed/partial import does not unpublish city.
2. Import/enrichment does not unpublish published place.
3. Admin overview separates manual review / auto backlog / low confidence.
4. Telegram moderation ignores draft/auto_backlog.
5. Repair script dry-run never writes DB.
6. Auto backlog processor uses cursor/batches and reports counters.
7. Duplicate photo candidates upsert/do-nothing.
8. Invalid `review_queue_items.job_id` does not violate FK.

### P2 — fixture cleanup

1. Split publication state factories.
2. Add factory assertions for impossible mixed states.
3. Remove hidden assumptions from default `place_factory` in publication tests.
4. Add helper for creating ReviewQueueItem place-change reviews.

### P3 — coverage/reporting

1. Make changed-files coverage actionable: fail if changed production files have no direct tests for critical areas.
2. Report uncovered changed files in Telegram summary.
3. Add mapping `changed file -> expected test modules` for admin/import/publication/Telegram.
4. Add test taxonomy markers: `admin`, `publication`, `import`, `telegram`, `route`, `performance`, `health`, `migration`.

## Required guard tests to add next

```text
tests/test_legacy_source_of_truth_contracts.py
```

Extend with:

1. `city_admin_import_jobs` is the active admin import source of truth.
2. `city_import_jobs` is not imported by admin overview/import monitor services.
3. `telegram_bot.main.create_dispatcher()` includes only active routers.
4. `routers/user_routes.py` does not import `services.itinerary_*`.
5. `frontend/package.json` lint script does not contain `|| true`.

## Definition of Done for test system cleanup

Autotest system can be considered controlled only when:

1. CI runs automatically on main/PR.
2. Frontend lint can fail CI.
3. Critical endpoint/service/model chains have guard tests.
4. Legacy source-of-truth artifacts are guarded by tests, not only docs.
5. Publication/import/Telegram regressions are covered by direct scenario tests.
6. Query-budget tests cover all admin dashboard summaries and latest-import queries.
7. Test fixtures do not silently create published/visible data in negative-state tests.
8. CI report lists missing scenario titles and uncovered changed files.
