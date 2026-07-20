# Public route entrypoint inventory (CITYGO-357)

Дата: 2026-07-20. Источник истины: `core/router_setup.py::_ROOT_ROUTERS` /
`include_app_routers()` — только реально зарегистрированные роутеры, не
имена файлов и не комментарии. Каждый путь ниже прослежен до реального
вызывающего кода (`grep`/чтение исходников), а не выведен по аналогии.

Дополняет (не заменяет) `docs/routes/route_current_state_audit.md`
(2026-06-10) — тот документ покрывает pipeline-стадии и user geolocation
UX; этот документ покрывает полный список зарегистрированных
route-related HTTP-эндпоинтов и их публикационный/eligibility контракт.

## 1. Canonical dynamic route pipeline (public)

| Router : Endpoint | Класс | Service call path | Candidate/place source | City publication gate | Place visibility/eligibility gate | Status owner | Diagnostics owner | Состояние |
|---|---|---|---|---|---|---|---|---|
| `routers/user_routes.py : POST /v1/user-routes/build` | public | `UserRouteBuildService.build` → (mode="slot" → `UserRouteSlotBuildService`) / (иначе → `RouteBuilderService.build_route` → `RouteEngine.build` → `InstantRouteStrategy` → `build_dynamic_route`) | `CandidateRetrievalService._base_query` (CITYGO-355 fix) | `public_route_eligible_sql_conditions()` → `public_place_conditions()`: `City.is_active AND launch_status=="published"` | `public_place_conditions()` + `is_route_eligible` | `RouteFinalizeService`/`route_status()` (canonical), с последующим только-понижающим уточнением в `build_dynamic_route::_apply_adaptive_metadata` (никогда не поднимает до `ready`) | `route_pipeline_trace`, `_debug_payload` в `CandidateRetrievalService`, `pipeline_trace` в `FinalRoute` | ACTIVE |
| `routers/user_routes.py : POST /v1/user-routes/preview` | public | то же, что `/build`, плюс `status="preview"` override и `_failed_preview` fallback | то же | то же | то же | то же (переопределяется только на `"preview"`/`"preview_failed"` — не поднимает `ready`) | то же | ACTIVE |
| `routers/user_routes.py : POST /v1/user-routes/build-structured` | public | `UserRouteEditService.structured_options` | `public_route_place_query()` (`services/public_route_place_access.py`) | `resolve_intent_scope` → `resolve_public_city_scope`: `is_active AND launch_status=="published"` | `apply_public_route_eligible_filters()` | N/A (options list, no single route status) | — | ACTIVE (verified baseline confirmed) |
| `routers/user_routes.py : POST /v1/user-routes/correct` | public | `RouteStateLifecycleService.correct` | зависит от action; мутации идут через `public_route_place_access.py` helpers | то же | то же | `RouteFinalizeService`/`route_status()` | — | ACTIVE (verified baseline confirmed) |
| `routers/user_routes.py : POST /v1/user-routes/{route_id}/update` | public | `RouteStateLifecycleService.update_order` | не меняет места, только порядок | наследуется от текущего `UserRouteState` | наследуется | canonical | — | ACTIVE |
| `routers/user_routes.py : POST /v1/user-routes/{route_id}/replace-place` | public | `RouteStateLifecycleService.replace_place` | `public_route_place_access.py` helpers | то же | то же | canonical | — | ACTIVE |
| `routers/user_routes.py : GET,POST /v1/user-routes/{route_id}/alternatives/{place_id}` | public | `RouteStateLifecycleService.read_alternatives` | `public_route_place_access.py` helpers | то же | то же | N/A (read) | — | ACTIVE |
| `routers/user_routes.py : POST /v1/user-routes/{route_id}/add-place` | public | `RouteStateLifecycleService.add_place` | `public_route_place_access.py` helpers | то же | то же | canonical | — | ACTIVE |
| `routers/user_routes.py : POST /v1/user-routes/{route_id}/session/start` | public | `RouteStateLifecycleService.start_session` | n/a (starts session on an existing `UserRouteState`) | наследуется от route state (см. verified baseline: sessions start only from `ready`/`partial_route`) | наследуется | n/a | — | ACTIVE (verified baseline confirmed) |
| `routers/user_routes.py : POST /v1/user-routes/sessions/{session_id}/action` | public | `UserRouteSessionService.apply_action` | n/a | наследуется | наследуется | n/a | — | ACTIVE |

Slot mode (`build_mode`/plan `mode == "slot"`): `UserRouteSlotBuildService.build`
использует `public_route_place_query()`/`load_public_route_place()`
(`services/public_route_place_access.py`) — полный публичный контракт.
Status: `RouteFinalizeService`/`route_status()` — единственный владелец
готовности; Slot Builder только понижает `ready → partial_route`, никогда
не повышает (CITYGO-356 fix).

## 2. Recommendation route (public, legacy-named but active)

| Router : Endpoint | Класс | Service call path | Candidate source | City gate | Place gate | Status owner | Diagnostics | Состояние |
|---|---|---|---|---|---|---|---|---|
| `routers/recommendations.py : POST /recommendations/route` и `POST /v1/recommendations/route` (тот же router, зарегистрирован дважды в `router_setup.py`) | public | `RouteBuilderService.build_route` (тот же canonical pipeline, что `/user-routes/build`) | `CandidateRetrievalService` | то же, что выше | то же | `RouteFinalizeService`/`route_status()` + `_apply_adaptive_metadata` | `ExplainabilityService`, `pipeline_trace` (за `X-Debug` header) | ACTIVE. `/recommendations/route` (без `/v1`) помечен `Deprecation`/`Sunset` HTTP-заголовками (`SUNSET_HTTP_DATE = "Tue, 30 Jun 2026 00:00:00 GMT"` — дата уже прошла на момент этого inventory, endpoint остаётся зарегистрированным и рабочим) |

Гейты toggle: `assert_route_generation_allowed`, `assert_ai_recommendations`
(`services/route_toggle_guard.py`, `services/feature_toggle_guards.py`) —
kill-switch'и, не публикационный контракт.

## 3. Random/draft route (public) — CITYGO-357 defect found and fixed

| Router : Endpoint | Класс | Service call path | Candidate source | City gate (до фикса) | City gate (после фикса) | Place gate | Status owner | Состояние |
|---|---|---|---|---|---|---|---|---|
| `routers/route_drafts.py : POST /routes/random` | public | `route_random_service.create_random_route_draft` | `route_draft_rules.eligible_place_query` | **ОТСУТСТВОВАЛ** — `compile_route_eligible_sql_conditions()` (place-level only), запрос вообще не join'ил `City` | `public_route_eligible_sql_conditions()` + explicit `City` join | place-level route eligibility (не изменилось) | draft-level `warnings`/`used_fallback`, не `route_status()` | ACTIVE, FIXED (см. §"New defects found") |
| `routers/route_drafts.py : GET /routes/drafts/{draft_id}` | public | `route_draft_loader.get_draft_or_error` | n/a (читает уже сохранённый draft) | n/a | n/a | n/a | n/a | ACTIVE |
| `routers/route_drafts.py : POST /routes/drafts/{draft_id}/remove-point` | public | `route_draft_mutations.remove_point` | n/a | n/a | n/a | n/a | n/a | ACTIVE |
| `routers/route_drafts.py : POST /routes/drafts/{draft_id}/add-point` | public | `route_draft_mutations.add_point` → `route_draft_loader.eligible_place_or_error` → `route_draft_rules.eligible_place_query` | same `eligible_place_query` fixed for `/routes/random` above | было отсутствие (same helper) | исправлено automatically (same helper, no separate change needed) | — | ACTIVE, FIXED (inherits the `/routes/random` fix — verified by reading `route_draft_loader.py::eligible_place_or_error`) |
| `routers/route_drafts.py : POST /routes/drafts/{draft_id}/replace-point` | public | `route_draft_mutations.replace_point` → same `eligible_place_or_error` | same | было отсутствие | исправлено automatically | — | ACTIVE, FIXED (same as above) |
| `routers/route_drafts.py : GET /routes/drafts/{draft_id}/search-places` | public | `route_draft_search.search_places` → `route_draft_rules.eligible_place_query` | тот же fix, что и `/routes/random` | было отсутствие | исправлено (тот же helper) | place-level (не изменилось) | n/a | ACTIVE, FIXED |

## 4. Editorial Route (curated, DB-stored, not Place-candidate pipeline)

| Router : Endpoint | Класс | Service call path | Source | Publication gate (до фикса) | Publication gate (после фикса) | Состояние |
|---|---|---|---|---|---|---|
| `routers/routes.py : GET /routes/` | public | `route_service.get_public_routes` / `get_public_routes_by_city_id` / `get_public_routes_by_city_slug` | `models.route.Route` | **ОТСУТСТВОВАЛ** — `Route.is_active` не проверялся, хотя `services/admin_service.py::publish_route/unpublish_route` явно используют его как publication toggle (audit log actions `publish_route`/`unpublish_route`) | `Route.is_active.is_(True)` | ACTIVE, FIXED |
| `routers/routes.py : GET /routes/by-slug/{slug}` | public | `route_service.get_public_route_by_slug` | то же | отсутствовал | исправлено | ACTIVE, FIXED |
| `routers/routes.py : GET /routes/{route_id}` | public | `route_service.get_public_route_by_id` | то же | отсутствовал | исправлено | ACTIVE, FIXED |
| `routers/routes.py : POST /routes/walking-geometry` | public | `walking_route_service.build_walking_route` | принимает точки напрямую от клиента, не читает `Route`/`Place` из БД | n/a | n/a | ACTIVE |
| `routers/route_places.py : GET /route-places/` | public | `route_place_service.get_route_places` / `get_route_places_by_route_id` | `models.route_place.RoutePlace` join `Route` | отсутствовал | `Route.is_active.is_(True)` | ACTIVE, FIXED |
| `routers/route_sessions.py : POST /routes/{route_id}/sessions` | public | `route_session_service.start_route_session` | `models.route.Route` | **уже был корректен**: `route.is_active` explicit check | без изменений | ACTIVE, verified correct (baseline) |
| `routers/route_sessions.py : GET /route-sessions/{session_id}` | public | `route_session_service.get_route_session` | n/a (читает уже созданную сессию) | n/a | n/a | ACTIVE |
| `routers/route_sessions.py : PATCH /route-sessions/{session_id}` | public | `route_session_service.update_route_session` | n/a | n/a | n/a | ACTIVE |
| `routers/route_sessions.py : POST /route-sessions/{session_id}/events/checkin` | public | `route_session_service.check_in_route_point` | n/a | n/a | n/a | ACTIVE |
| `routers/route_sessions.py : POST /route-sessions/{session_id}/complete` | public | `route_session_service.complete_route_session` | n/a | n/a | n/a | ACTIVE |

`admin_service.py::publish_route/unpublish_route`, `admin_extended_service.py`
(`update_admin_route`, `replace_admin_route_points`) и `routers/admin.py`'s
admin routes list (`get_admin_routes`) reuse `route_service.get_route_by_id`
/ `get_route_by_slug` / `get_routes*` — kept **unfiltered on purpose** so
admin can find and re-publish an already-unpublished route. See
"New defects found" §2 for why this distinction matters.

## 5. Legacy itinerary (deprecated but active) — CITYGO-357 defect found and fixed

Router docstring: *"LEGACY ROUTER for old itinerary endpoints... Do not add
new route features here. Keep old endpoints only for compatibility until
consumers migrate."*

| Router : Endpoint | Класс | Service call path | Candidate source | City gate (до фикса) | City gate (после фикса) | Status owner | Состояние |
|---|---|---|---|---|---|---|---|
| `routers/itinerary.py : POST /routes/generate` (`deprecated=True` in FastAPI route decorator, `X-Deprecated` response header) | public | `itinerary_service.generate_itinerary_stub` → `itinerary_candidate_service.get_candidate_places` | `models.place.Place` | **ОТСУТСТВОВАЛ** — `apply_route_eligible_filters()` (place-level only), `get_city_by_slug` без publication check | `apply_public_route_eligible_filters()` | собственная логика в `itinerary_service.py` (не `route_status_service`) | ACTIVE (deprecated), FIXED |
| `routers/itinerary.py : POST /routes/replan` | public | `itinerary_replan_service.replan_itinerary` → `load_route_places` / `load_preferred_stop_place` / `find_best_stop_place` | `models.place.Place` | `load_route_places`/`load_preferred_stop_place`: **ОТСУТСТВОВАЛ** (тот же класс дефекта). `find_best_stop_place`: **уже был корректен** — вызывает `evaluate_place_route_eligibility(place, city=city)`, которая проверяет `city.launch_status`/`is_active` через `_city_reason()` | `load_route_places`/`load_preferred_stop_place`: `apply_public_route_eligible_filters()`. `find_best_stop_place`: без изменений (не требовалось) | своя логика | ACTIVE, PARTIALLY FIXED (2 из 3 мест были дефектны, все 3 используют один и тот же helper теперь) |

Gate toggle: `assert_route_generation_allowed` — kill-switch, не публикационный контракт.

## 6. Admin preview / dry-run (admin-only, auth-gated)

| Router : Endpoint | Класс | Service call path | Candidate source | Auth | Состояние |
|---|---|---|---|---|---|
| `routers/admin_route_ops.py : POST /admin/routes/dry-run` | admin | `AdminRouteDryRunService.run` | `CandidateRetrievalService(is_admin=True)` → `admin_preview_route_eligible_sql_conditions()` (city publication intentionally not required) | `admin_required` | ACTIVE, verified correct (baseline) |
| `routers/admin_route_ops.py : POST /admin/routes/drafts/generate` | admin | `admin_route_draft_pipeline.generate_admin_route_draft` | не re-verified в этой итерации (не в scope доказанных дефектов) | `admin_required` | NOT FULLY VERIFIED |
| `routers/admin_route_ops.py : POST /admin/routes/drafts/{draft_id}/publish` | admin | `admin_route_draft_pipeline.publish_admin_route_draft` | n/a (публикует уже существующий draft) | `admin_required` | ACTIVE |
| `routers/admin_route_ops.py : GET /admin/routes/debug-last` | admin | `route_pipeline_trace.get_last_route_debug` | n/a (in-process debug state) | `admin_required` | ACTIVE |
| `routers/admin_route_eligibility.py : GET /admin/routes/eligibility`, `/eligibility/{city_slug}`, `/data-quality/{city_slug}`, `/readiness*` | admin | `route_eligibility_dashboard`, `city_readiness` services | read-only diagnostics, no candidate retrieval | `admin_required` (assumed — not re-verified line-by-line in this pass) | NOT FULLY VERIFIED (read-only diagnostics, low risk) |

## 7. Telegram route flow

`telegram_bot/services/recommendation_client.py::RecommendationApiClient`
is a plain HTTP client — it calls `POST {backend}/v1/user-routes/build` and
`POST {backend}/v1/user-routes/correct` over `httpx`. **No separate
candidate-retrieval or publication logic exists in the Telegram layer** —
it fully inherits the canonical pipeline's contract (§1 above), including
the CITYGO-355/356 fixes. Verified by `grep` across `telegram_bot/` for any
direct `CandidateRetrievalService`/`eligible_place_query`/
`RouteBuilderService` import: none found.

## 8. Destination-aware and feature-flag paths

- **Destination-aware**: `services/destination_route_resolution.py::resolve_route_build_request`
  only resolves `destination_slug`/`destination_id` → `city_id` (a mapping
  step); it does not perform its own candidate retrieval. The actual
  destination-membership filter is
  `CandidateRetrievalService::_apply_destination_membership_route_filter`,
  gated by `services/destination_flags.py::destination_route_reads_enabled()`
  — this is the same `_base_query()` fixed under CITYGO-355 and is exercised
  by `tests/test_candidate_retrieval_public_route_contract_new.py::test_destination_route_reads_disabled_by_default_preserves_public_contract_new`.
- **Feature-flag paths**: `assert_route_generation_allowed` (global +
  city-scoped kill switches), `assert_ai_recommendations` — both are
  binary on/off gates, not publication/visibility contracts; not in scope
  for this inventory's publication/eligibility verification.

## New defects found (proven with a failing test before fixing, per task rule)

1. **`services/route_draft_rules.py::eligible_place_query`** (used by
   `POST /routes/random` and `GET /routes/drafts/{id}/search-places`) had
   NO city publication gate at all (place-level-only filter, no `City`
   join). Fixed: joins `City`, uses `public_route_eligible_sql_conditions()`.
   Tests: `tests/test_route_draft_public_route_contract_new.py` (5 tests,
   confirmed failing on the pre-fix code, then passing).
2. **`services/route_service.py`** (`GET /routes`, `/routes/{id}`,
   `/routes/by-slug/{slug}`) never filtered on `Route.is_active`, even
   though `services/admin_service.py::publish_route/unpublish_route`
   explicitly toggle that field as a publication gate (audit-logged
   `publish_route`/`unpublish_route` actions). Fixed by adding
   publication-gated `get_public_route_*`/`get_public_routes*` variants and
   switching `routers/routes.py` to them, while leaving
   `get_route_by_id`/`get_route_by_slug`/`get_routes*` unfiltered — those
   are reused by admin edit/publish code
   (`services/admin_service.py`, `services/admin_extended_service.py`),
   which must still be able to load an unpublished route (e.g. to
   re-publish it). This distinction was caught during implementation: an
   initial version filtered the shared functions directly, which broke
   `publish_route`/`unpublish_route`'s own ability to find an already
   unpublished route — reverted before committing.
   `services/route_place_service.py` (`GET /route-places`, the only public
   caller, no admin caller to preserve) is filtered directly. Tests:
   `tests/test_route_service_publication_gate_new.py` (14 tests: 8 confirm
   the public path is now gated, 6 confirm the internal/admin path is
   deliberately still unfiltered).
3. **Legacy itinerary stack** (`POST /routes/generate`,
   `POST /routes/replan`) — `services/itinerary_candidate_service.py::get_candidate_places`
   and `services/itinerary_replan_service.py::load_route_places` /
   `load_preferred_stop_place` used the place-level-only
   `apply_route_eligible_filters()` with no city publication check.
   `find_best_stop_place` was investigated and found NOT defective (already
   checks city publication via `evaluate_place_route_eligibility(place,
   city=city)`) — verified directly before writing any assertion about it,
   to avoid a false-positive regression claim. Fixed the two genuinely
   defective functions by switching to
   `apply_public_route_eligible_filters()`. Tests:
   `tests/test_itinerary_legacy_public_route_contract_new.py` (7 tests,
   confirmed failing on the pre-fix code for the 2 defective functions,
   passing for the non-defective one both before and after).

All three defects are the same root-cause class as CITYGO-355
(place-level-only eligibility filter used where the complete public route
contract — city publication + place visibility — was required), just in
different call paths than `CandidateRetrievalService`. No architecture
change: every fix reuses the existing canonical helpers
(`public_route_eligible_sql_conditions`, `apply_public_route_eligible_filters`,
`public_place_conditions`) — no new business rule was written.

## Unknown / not fully verified (explicit, not guessed)

- `routers/admin_route_ops.py : POST /admin/routes/drafts/generate` — admin,
  auth-gated, not re-verified line-by-line for its candidate source in this
  pass. Missing evidence: full read of `services/admin_route_draft_pipeline.py::generate_admin_route_draft`.
- `routers/admin_route_eligibility.py` — admin-only read diagnostics;
  `admin_required` dependency presence assumed from the file's naming and
  sibling routers' pattern, not individually re-confirmed for every one of
  its 6 endpoints in this pass.

None of the above were treated as confirmed defects — they are explicitly
marked as unverified per the task's "unknown paths are not guessed" rule,
not silently assumed safe.
