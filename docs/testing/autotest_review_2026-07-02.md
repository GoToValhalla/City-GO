# CITY GO — Autotest Review 2026-07-02

Цель: зафиксировать ревью автотестов после регрессий в admin/publication/import/Telegram/route flows.

## Обновление 2026-07-02

Добавлены и/или обновлены:

- `.github/workflows/ci.yml` — Full Autotests запускается на push/pull_request в main и вручную.
- `frontend/package.json` — lint возвращает реальный exit code.
- `tests/conftest.py` — добавлены explicit place state factories.
- `tests/test_ci_and_active_contract_guards.py` — guard для CI и active source-of-truth.
- `tests/test_legacy_source_of_truth_contracts.py` — guard для `/admin/place-change-reviews/* -> ReviewQueueItem`.
- `tests/test_publication_fixture_and_migration_contracts.py` — contracts для factories и critical tables.
- `tests/test_mobile_review_manual_queue_regression.py` — regression pack для manual moderation queue.
- `tests/test_publication_auto_backlog_regression.py` — regression pack для auto backlog publication policy.
- `tests/test_ci_reporting_contracts.py` — contracts для CI summary parser/renderer.
- `docs/admin/publication_state_invariants.md` — source-of-truth chain rule.
- `docs/architecture/legacy_code_register.md` — legacy source-of-truth register.

## Закрыто

### CI gate

- Full Autotests больше не manual-only.
- Frontend lint больше не подавляется через always-green команду.
- Добавлен backend import smoke до полного regression.

### Source of truth guards

Зафиксированы active chains:

```text
/admin/place-change-reviews/*
  -> services/place_change_review_service.py
  -> ReviewQueueItem
  -> field_name='place_change'
  -> status='open'
```

```text
/admin/import-jobs/*
  -> CityAdminImportJob
  -> city_admin_import_jobs
```

```text
routers/user_routes.py
  -> UserRouteBuildService
  -> active route builder flow
```

```text
telegram_bot/main.py
  -> admin_moderation_router
  -> catalog_router
```

### Explicit place state factories

Добавлены fixtures:

- `published_place_factory`
- `draft_place_factory`
- `manual_review_place_factory`
- `auto_backlog_place_factory`
- `hidden_place_factory`

Они нужны, чтобы tests явно задавали product/manual/auto publication state и не полагались на default happy-path `place_factory`.

### Fixture/schema contracts

Добавлены проверки:

- metadata содержит `review_queue_items`, `city_admin_import_jobs`, `place_photo_candidates`, `place_publication_decisions`, `admin_audit_logs`;
- test DB содержит эти critical tables после `create_all`;
- `review_queue_items.job_id` nullable для non-import/manual items;
- `place_photo_candidates` имеет unique contract по `(place_id, image_url)`.

### Manual moderation regression pack

Покрыто:

- draft и auto backlog не попадают в manual moderation queue;
- manual queue показывает только explicit manual statuses;
- publish из moderation выставляет полный public state.

### Auto backlog regression pack

Покрыто:

- trusted official draft auto-publishes without photo;
- low confidence без trusted address остаётся auto backlog и не попадает в manual queue;
- duplicate suspected не публикуется automatically.

### CI reporting contracts

Покрыто:

- CI summary выводит блок Allure scenario coverage;
- CI summary парсит JUnit failure и показывает actionable failure details.

## Текущий открытый долг

### DB/test architecture

1. Полностью развести Alembic integration DB и metadata-only unit DB.
2. Ввести marker `metadata_db`.
3. Для admin/API/integration tests использовать Alembic-created DB.
4. Оставить `Base.metadata.create_all()` только для unit/model tests.

### Regression depth

1. Failed/partial import does not unpublish city.
2. Import/enrichment does not unpublish published place.
3. Repair script dry-run never writes DB.
4. Auto backlog processor uses cursor/batches and reports counters.
5. Duplicate photo candidates runtime insert does not crash.
6. Invalid `review_queue_items.job_id` creation path is guarded.
7. Query-budget coverage для latest import per city, Telegram moderation, admin summaries и repair scripts.

### CI reporting quality

1. Report tests without readable scenario title.
2. Report uncovered changed files in Telegram summary.
3. Add mapping `changed file -> expected test modules`.
4. Add taxonomy markers: `admin`, `publication`, `import`, `telegram`, `route`, `performance`, `health`, `migration`.

## Definition of Done status

1. CI runs automatically on main/PR — done.
2. Frontend lint can fail CI — done.
3. Critical endpoint/service/model chains have guard tests — expanded.
4. Legacy source-of-truth artifacts are guarded by tests — expanded.
5. Publication/import/Telegram regressions are covered by direct scenario tests — expanded, not exhaustive.
6. Query-budget tests cover all admin summaries and latest-import queries — partial.
7. Negative-state tests have explicit fixtures — added; default fixture remains backward-compatible.
8. CI report lists missing scenario titles and uncovered changed files — not done.
