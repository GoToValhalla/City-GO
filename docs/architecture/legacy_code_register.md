# CITY GO — Legacy Code Register

Дата начала реестра: 2026-07-02
Последнее обновление: 2026-07-02

Назначение: фиксировать код, который больше не является source of truth, но сохраняется как историческая реализация. Такой код не удаляется сразу, но должен быть явно помечен как `LEGACY`, описан и запрещён для нового использования.

## Правила работы с legacy

1. Не удалять сразу, если код связан с миграциями, историческими данными или production rollback.
2. Помечать в начале файла или класса:
   - статус;
   - как работало;
   - почему legacy;
   - чем заменено;
   - что запрещено.
3. Не использовать legacy-модели/сервисы в новых endpoint/test fixtures.
4. Активный source of truth должен быть указан явно.
5. Любой endpoint должен проверяться по цепочке: router -> service -> model/table -> tests.
6. Если статус legacy не доказан, код не отключать и не переименовывать.
7. Если GitHub/CI не даёт безопасно переписать файл, фиксировать статус в этом реестре до отдельного PR.

## Реестр

| Область | Legacy artifact | Статус | Active source of truth | Комментарий |
|---|---|---|---|---|
| Public catalog change review | `models/place_change_review.py` / `PlaceChangeReview` / table `place_change_reviews` | LEGACY, historical compatibility only | `models/review_queue_item.py` / `ReviewQueueItem` with `field_name='place_change'`, `status='open'` | Старый row-per-field workflow. Активные `/admin/place-change-reviews/*` endpoint'ы читают `ReviewQueueItem`, не `PlaceChangeReview`. |
| Admin extra endpoints | `routers/admin_extra.py`, `services/admin_extra_service.py`, `schemas/admin_extra.py` | LEGACY, router not registered | Active admin overview/coverage/platform/route feedback routers and services | Старые `/admin/roles`, `/admin/cities/{id}/coverage`, `/admin/route-feedback`. `routers.admin_extra` не подключён в `core/router_setup.py`; не регистрировать обратно без migration task. |
| Publication reconciliation CLI | `scripts/reconcile_publication_flags.py` | LEGACY COMPATIBILITY CLI | `scripts/diagnose_publication_states.py`, `scripts/repair_publication_states.py`, `services/publication_reconciliation_service.py` | Старый операторский entrypoint. Оставлен для visibility-toggle materialization и rollback compatibility. Не использовать как основной repair path. |
| Publication policy batch runner | `scripts/run_publication_policy.py` | LEGACY OPERATOR CLI | `scripts/auto_process_publication_backlog.py`, `services/publication_policy.py`, будущий batch processor с тестами | Старый runner по unpublished active places. Не использовать как основной путь для 17k backlog и не вешать на новые admin buttons без batch/audit tests. |
| Import jobs | `models/city_import_job.py` / table `city_import_jobs` | LEGACY/SCOPE SCHEDULER STORAGE, not admin dashboard source of truth | `models/city_admin_import_job.py` / table `city_admin_import_jobs` for admin import monitor | Старый scope/cron import foundation. Не использовать для admin latest import status и не менять через него product city state. |
| Import job service | `services/import_job_service.py` | LEGACY/SCOPE SCHEDULER SERVICE | `services/admin_city_import_job_service.py`, `services/admin_city_import_runner.py` for admin imports | Использует `CityImportJob` и `CityImportScope`. Не использовать для admin import dashboard и publication state. |
| Legacy itinerary route endpoints | `routers/itinerary.py` | LEGACY COMPATIBILITY ROUTER, registered until clients migrate | `routers/user_routes.py`, `/v1/user-routes/*` | `/routes/generate` deprecated and sends `X-Deprecated: Use POST /v1/user-routes/build instead`. Новые route-фичи сюда не добавлять. |
| Legacy itinerary generation stack | `services/itinerary_service.py`, `services/itinerary_route_builder_service.py`, `services/itinerary_candidate_service.py`, `services/itinerary_scoring_service.py` | LEGACY ITINERARY DRAFT STACK until route product consolidation | `services/route_builder_flow.py`, `services/user_route_build_service.py`, route draft/session services | Старая ветка генерации itinerary. Не удалять: может обслуживать old endpoint/schema. Новые route features должны идти через route builder/user route flow. |
| Admin overview old semantics | old use of `verification_status in ('needs_recheck','unverified')` as `needs_review` | DEPRECATED SEMANTIC | `manual_review = Place.publication_status in ('needs_review','needs_manual_review','deferred')` | Verification backlog должен называться отдельно `needs_verification`, не “Требуют проверки”. |
| Product publication repair | direct SQL/manual flag reset scripts | FORBIDDEN LEGACY PRACTICE | `scripts/repair_publication_states.py` with dry-run snapshot | Любой direct reset `City.is_active`, `City.launch_status`, `Place.is_published` без snapshot/reason/audit запрещён. |

## Подтверждённые кейсы

### 1. `PlaceChangeReview` vs `ReviewQueueItem`

Фактическая цепочка активного endpoint:

```text
routers/admin_place_change_review.py
  -> services/place_change_review_service.py
  -> _open_review_row()
  -> ReviewQueueItem
  -> field_name='place_change'
  -> status='open'
```

Что было ошибкой:

- тесты и фиксы создавали `PlaceChangeReview`, потому что модель называлась похоже;
- endpoint при этом искал `ReviewQueueItem`, поэтому approve/reject возвращали 404 или падали на NOT NULL constraints;
- это показало, что в проекте есть неразмеченные legacy-дубли.

Текущее решение:

- `PlaceChangeReview` оставлен как историческая модель;
- файл помечен как `LEGACY MODEL`;
- новый код не должен использовать эту модель;
- active review workflow — только `ReviewQueueItem`.

### 2. Publication reconciliation CLI

Фактическая новая модель:

```text
scripts/diagnose_publication_states.py        # диагностика без изменения БД
scripts/repair_publication_states.py          # repair с dry-run snapshot
services/publication_reconciliation_service.py # non-destructive by default
```

Старый `scripts/reconcile_publication_flags.py` оставлен как compatibility wrapper. Новые production repair-действия не должны начинаться с него.

### 3. Import job storage split

В проекте есть две линии import jobs:

```text
city_import_jobs          # старый scope scheduler / cron foundation
city_admin_import_jobs    # admin import monitor / current admin source of truth
```

Для admin UI, latest import status, import failed/running/stale используется `city_admin_import_jobs`. `city_import_jobs` не должен влиять на product publication state.

### 4. Route/itinerary split

Старая ветка:

```text
routers/itinerary.py -> itinerary_service -> itinerary_candidate/scoring/route_builder
```

Новая/активная route-ветка:

```text
routers/user_routes.py -> route_builder_flow -> user_route_build_service -> route drafts/sessions
```

До полной миграции old itinerary stack не удалять, но новые route features не добавлять туда без отдельного решения.

### 5. Admin extra split

`routers/admin_extra.py` есть в коде, но не подключён в `core/router_setup.py`. Это исторический router ранней админки.

Активные admin sections сейчас разведены по специализированным routers/services:

```text
admin_overview_service
admin_coverage_metrics / admin_coverage_gaps
admin_platform*
route_feedback active flow
```

`admin_extra` не должен возвращаться как быстрый способ добавить старые endpoints.

## Запреты для новых изменений

1. Не создавать новые фикстуры через `PlaceChangeReview`.
2. Не читать active `/admin/place-change-reviews/*` из `place_change_reviews`.
3. Не считать `verification_status` ручной очередью.
4. Не использовать `city_import_jobs` для admin latest import status.
5. Не использовать `scripts/reconcile_publication_flags.py` как основной production repair.
6. Не добавлять новые route features в legacy itinerary stack без архитектурного решения.
7. Не делать direct reset publication flags без `repair_publication_states.py` или explicit audited admin action.
8. Не регистрировать `routers.admin_extra` обратно без отдельной migration task.

## Проверка перед фиксом

Перед изменением любого endpoint/service нужно записать фактическую цепочку:

```text
router -> service -> model/table -> status field -> tests
```

Если в цепочке есть legacy artifact, его нельзя использовать как source of truth.
