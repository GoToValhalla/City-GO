# CITY GO — Autotest Review 2026-07-02

Цель: зафиксировать полный ревью-контур автотестов после регрессий в admin/publication/import/Telegram/route flows и сразу отделить выполненные P0-фиксы от оставшегося долга.

## Проверенный scope

Проверены и зафиксированы:

- `.github/workflows/ci.yml`
- `frontend/package.json`
- `tests/conftest.py`
- `tests/test_public_catalog_e2e_regression.py`
- `tests/test_legacy_source_of_truth_contracts.py`
- `tests/test_ci_and_active_contract_guards.py`
- `routers/admin_place_change_review.py`
- `services/place_change_review_service.py`
- `routers/admin_import_jobs.py`
- `services/admin_city_import_job_service.py`
- `services/admin_import_jobs_fast.py`
- `routers/user_routes.py`
- `telegram_bot/main.py`
- `docs/admin/publication_state_invariants.md`
- `docs/architecture/legacy_code_register.md`

## Выполнено сразу в рамках ревью

1. Full Autotests больше не manual-only: `.github/workflows/ci.yml` теперь запускается на `push` в `main`, `pull_request` в `main` и `workflow_dispatch`.
2. Frontend lint больше не подавляется: `frontend/package.json` заменён с подавляющего варианта на lint-команду, которая возвращает реальный exit code.
3. Добавлен guard `tests/test_ci_and_active_contract_guards.py`, который проверяет:
   - admin import использует `CityAdminImportJob`, а не legacy `CityImportJob`;
   - active user route router не импортирует legacy `services.itinerary_*`;
   - Telegram dispatcher не регистрирует legacy `telegram_bot/handlers/route.py`;
   - frontend lint не подавлен;
   - Full Autotests не manual-only.
4. Уже существующий guard `tests/test_legacy_source_of_truth_contracts.py` защищает `/admin/place-change-reviews/*` от повторного использования legacy `PlaceChangeReview`.
5. `docs/admin/publication_state_invariants.md` обновлён правилом `router -> service -> model/table -> status field -> tests`.

## Главные найденные проблемы

### 1. CI ранее не был полноценным gate

До фикса `Full Autotests` имел только ручной запуск. Это означало, что main мог получать изменения без автоматического полного regression gate.

Статус: исправлено в `.github/workflows/ci.yml`.

### 2. Frontend lint ранее не мог валить CI

В `frontend/package.json` был suppressor:

```json
"lint": "eslint . || true"
```

Статус: исправлено; lint теперь возвращает настоящий exit code.

### 3. Backend тестовая БД смешивает Alembic и metadata schema

В `tests/conftest.py` одновременно есть:

- session-level Alembic migration для `settings.database_url`;
- in-memory SQLite через `Base.metadata.create_all()` для fixtures.

Риск: тесты могут проходить на metadata schema, но ломаться на migration schema. Это уже проявлялось через NOT NULL/FK ошибки в review моделях.

Нужно отдельным исправлением:

- ввести marker `metadata_db` для metadata-only tests;
- integration/admin/API tests перевести на Alembic-created DB;
- добавить migration contract tests для NOT NULL/FK/unique constraints критичных таблиц.

### 4. Fixtures по умолчанию создают слишком happy-path данные

`place_factory` по умолчанию создаёт published/visible/route eligible/searchable place.

Риск: negative-state tests становятся ложноположительными, потому что published state уже выставлен фабрикой.

Нужно отдельным исправлением:

- добавить explicit factories:
  - `published_place_factory`;
  - `draft_place_factory`;
  - `manual_review_place_factory`;
  - `auto_backlog_place_factory`;
  - `hidden_place_factory`;
- для publication/admin/import tests запретить неявное использование default published state.

### 5. Legacy source-of-truth confusion теперь защищён guard tests

Зафиксированный инцидент:

```text
/admin/place-change-reviews/*
  -> services/place_change_review_service.py
  -> ReviewQueueItem(field_name='place_change', status='open')
```

Ошибка была в использовании `PlaceChangeReview`, потому что модель называлась похоже. Теперь это защищено guard tests и legacy register.

Статус: частично исправлено guard-тестами. Нужно расширять такой подход на новые legacy-дубли по мере подтверждения.

### 6. Сценарное покрытие Allure слабое

CI summary показывал около 52% explicit Russian scenarios. Значит, часть тестов технические, а не сценарные.

Нужно:

- каждый regression по production incident должен иметь человекочитаемый scenario title;
- критичные admin/import/publication/Telegram tests должны иметь readable title;
- CI summary должен показывать список тестов без readable title, а не только процент.

### 7. Query-budget coverage недостаточно системное

Есть budget checks для части admin overview/coverage, но нужны отдельные checks для:

- latest import job per city;
- Telegram moderation city list/next item;
- admin city table summaries;
- auto backlog batch cursor processing;
- publication diagnostics/repair scripts.

### 8. Production health coverage неполное

`/ready` должен быть быстрым и независимым от admin summaries. Нужны отдельные тесты:

- `/ready` не делает heavy DB/admin queries;
- `/ready` survives admin summary failures;
- worker startup smoke imports all registered routers/services;
- deploy/build smoke catches missing imports before pushing images.

## Оставшийся план исправлений

### P1 — DB/fixture correctness

1. Развести Alembic integration DB и metadata-only unit DB.
2. Добавить migration contract tests для:
   - `review_queue_items`;
   - `city_admin_import_jobs`;
   - `place_photo_candidates`;
   - publication/audit tables.
3. Добавить explicit place state factories.
4. Запретить default published fixture в publication/import/manual review tests.

### P2 — publication/import/admin regression pack

1. Failed/partial import does not unpublish city.
2. Import/enrichment does not unpublish published place.
3. Admin overview separates manual review / auto backlog / low confidence.
4. Telegram moderation ignores draft/auto_backlog.
5. Repair script dry-run never writes DB.
6. Auto backlog processor uses cursor/batches and reports counters.
7. Duplicate photo candidates upsert/do-nothing.
8. Invalid `review_queue_items.job_id` does not violate FK.

### P3 — CI reporting quality

1. Fail changed critical production files without matching direct tests.
2. Report uncovered changed files in Telegram summary.
3. Add mapping `changed file -> expected test modules` for admin/import/publication/Telegram.
4. Add test taxonomy markers: `admin`, `publication`, `import`, `telegram`, `route`, `performance`, `health`, `migration`.
5. List tests without readable scenario title.

## Definition of Done for test system cleanup

Autotest system can be considered controlled only when:

1. CI runs automatically on main/PR. Status: done.
2. Frontend lint can fail CI. Status: done.
3. Critical endpoint/service/model chains have guard tests. Status: started.
4. Legacy source-of-truth artifacts are guarded by tests, not only docs. Status: started.
5. Publication/import/Telegram regressions are covered by direct scenario tests. Status: partial.
6. Query-budget tests cover all admin dashboard summaries and latest-import queries. Status: partial.
7. Test fixtures do not silently create published/visible data in negative-state tests. Status: not done.
8. CI report lists missing scenario titles and uncovered changed files. Status: not done.
