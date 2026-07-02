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
| Refresh all cities script | `scripts/refresh_all_cities.py` | LEGACY/SCOPE REFRESH OPERATOR SCRIPT | admin import queue/job services and `CityAdminImportJob` | Старый production-container scope refresh через OSM import v2. Не использовать для publication repair и не считать его admin import source of truth. |
| Seed place import CLI | `scripts/production_place_import.py` | LEGACY SEED IMPORT CLI | admin import pipeline / audited import jobs / place discovery import flow | Старый ручной import seed JSON в `/place-seed/import/`. Не использовать как production city import path. |
| Legacy itinerary route endpoints | `routers/itinerary.py` | LEGACY COMPATIBILITY ROUTER, registered until clients migrate | `routers/user_routes.py`, `/v1/user-routes/*` | `/routes/generate` deprecated and sends `X-Deprecated: Use POST /v1/user-routes/build instead`. Новые route-фичи сюда не добавлять. |
| Legacy itinerary orchestration | `services/itinerary_service.py` | LEGACY ITINERARY ORCHESTRATION STACK | `services/route_builder_flow.py`, `services/user_route_build_service.py`, route draft/session services | Старая orchestration ветка для `/routes/generate`. |
| Legacy itinerary candidate retrieval | `services/itinerary_candidate_service.py` | LEGACY ITINERARY CANDIDATE SERVICE | `services/candidate_retrieval_service.py`, route eligibility query filters | Старый candidate retrieval для itinerary stack. Новые retrieval/filtering rules сюда не добавлять. |
| Legacy itinerary scoring | `services/itinerary_scoring_service.py` | LEGACY ITINERARY SCORING SERVICE | `services/scoring_service.py`, `services/route_quality_score.py`, `services/route_builder_flow.py` | Старый скоринг itinerary. Новые scoring-фичи сюда не добавлять. |
| Legacy itinerary route builder helpers | `services/itinerary_route_builder_service.py` | LEGACY ITINERARY ROUTE BUILDER HELPERS | `services/route_builder_flow.py`, route assembly/optimizer services | Старый helper stack для `/routes/generate`. |
| Admin overview old semantics | old use of `verification_status in ('needs_recheck','unverified')` as `needs_review` | DEPRECATED SEMANTIC | `manual_review = Place.publication_status in ('needs_review','needs_manual_review','deferred')` | Verification backlog должен называться отдельно `needs_verification`, не “Требуют проверки”. |
| Product publication repair | direct SQL/manual flag reset scripts | FORBIDDEN LEGACY PRACTICE | `scripts/repair_publication_states.py` with dry-run snapshot | Любой direct reset `City.is_active`, `City.launch_status`, `Place.is_published` без snapshot/reason/audit запрещён. |

## Подтверждённые кейсы

### 1. `PlaceChangeReview` vs `ReviewQueueItem`

```text
routers/admin_place_change_review.py
  -> services/place_change_review_service.py
  -> _open_review_row()
  -> ReviewQueueItem
  -> field_name='place_change'
  -> status='open'
```

### 2. Publication reconciliation CLI

```text
scripts/diagnose_publication_states.py
scripts/repair_publication_states.py
services/publication_reconciliation_service.py
```

### 3. Import job storage split

```text
city_import_jobs          # старый scope scheduler / cron foundation
city_admin_import_jobs    # admin import monitor / current admin source of truth
```

### 4. Route/itinerary split

```text
routers/itinerary.py -> itinerary_service -> itinerary_candidate/scoring/route_builder
routers/user_routes.py -> route_builder_flow -> user_route_build_service -> route drafts/sessions
```

### 5. Admin extra split

`routers/admin_extra.py` есть в коде, но не подключён в `core/router_setup.py`. Это исторический router ранней админки.

### 6. Import operator scripts split

```text
scripts/refresh_all_cities.py
scripts/production_place_import.py
```

Оставлены как operator compatibility/history, но не являются текущим source of truth для admin import monitor, publication state repair или массовой обработки backlog.

## Запреты для новых изменений

1. Не создавать новые фикстуры через `PlaceChangeReview`.
2. Не читать active `/admin/place-change-reviews/*` из `place_change_reviews`.
3. Не считать `verification_status` ручной очередью.
4. Не использовать `city_import_jobs` для admin latest import status.
5. Не использовать `scripts/reconcile_publication_flags.py` как основной production repair.
6. Не добавлять новые route features в legacy itinerary stack без архитектурного решения.
7. Не делать direct reset publication flags без `repair_publication_states.py` или explicit audited admin action.
8. Не регистрировать `routers.admin_extra` обратно без отдельной migration task.
9. Не использовать `refresh_all_cities.py` как текущий admin import pipeline.
10. Не использовать `production_place_import.py` как production city import path.
11. Не добавлять новые candidate retrieval/scoring/assembly rules в `services/itinerary_*`.

## Проверка перед фиксом

Перед изменением любого endpoint/service нужно записать фактическую цепочку:

```text
router -> service -> model/table -> status field -> tests
```

Если в цепочке есть legacy artifact, его нельзя использовать как source of truth.
