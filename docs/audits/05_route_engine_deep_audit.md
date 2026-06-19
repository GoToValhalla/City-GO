# 05 — Route Engine Deep Audit

> Deepest audit of the City Go route engine. No code changed. Every stage references concrete files/functions and quotes hardcoded limits.
> Classification: REAL DEFECT · TECHNICAL DEBT · PARTIALLY IMPLEMENTED · FUTURE ROADMAP · INTENTIONALLY DEFERRED · REQUIRES VERIFICATION

---

## 1. Executive Summary

The recommendation route engine is a clean, staged pipeline orchestrated by `services/route_builder_flow.py::build_dynamic_route` with good trace instrumentation (`route_pipeline_trace.py`) and honest user warnings. All 25 audited files exist. Routes can be **too short / inconsistent** because the candidate pool is narrowed by **a chain of silent hardcoded caps** (300 → 120 → `scored[:120]` → diversity caps → budget trim) without per-place drop diagnostics, and because `effective_num_stops` is capped at 6 while assembly targets 2–8.

Three concrete defects:

1. **`is_route_eligible` is not enforced in retrieval** (`candidate_retrieval_service.py:41-48` uses `public_place_conditions()`, not `public_route_place_conditions()`). Diagnostics counts it; retrieval ignores it → **diagnostics/retrieval mismatch**. → REAL DEFECT.
2. **A test targets a non-existent function** `_fallback_city_scope` (`tests/test_candidate_retrieval_city_scope_fallback_new.py`) — the production code only has `_fallback_expand_radius`. The test describes unimplemented behavior. → REAL DEFECT (false green / dead test).
3. **`route_candidate_diagnostics.py` has zero tests** and reports counts using a different filter than retrieval. → TECHNICAL DEBT (misleading observability).

A separate **legacy `itinerary` pipeline** (`routers/itinerary.py` → `itinerary_service`) does NOT use `RouteBuilderService` and is out of scope of recommendation stabilization. → TECHNICAL DEBT (duplicate engine).

---

## 2. Entry Point Map

| Entry | Router/Service | Uses RouteBuilderService? |
|---|---|---|
| `POST /recommendations/route` | `routers/recommendations.py::post_recommendation_route` → `RouteBuilderService.build_route` → `build_dynamic_route` | ✅ |
| `POST /v1/user-routes/build` | `routers/user_routes.py` → `UserRouteBuildService` → `RouteBuilderService` | ✅ |
| `POST /routes/generate`, `/replan` | `routers/itinerary.py` → `itinerary_service` / `itinerary_replan_service` | ❌ separate engine |

Public trace exposed only with `X-Debug: true` (`recommendations.py:77-78`).

---

## 3. Full Pipeline Map

Orchestrator `route_builder_flow.py::build_dynamic_route` (`:26-47`):
context_merge → candidate retrieval → quality annotation → hard filters → scoring → assembly → time ordering → time aware → budget fit + gap fill → finalize.

| Stage | File / Function | In → Out | Count change |
|---|---|---|---|
| 0. HTTP→ctx | `recommendations.py::post_recommendation_route` | request → `RequestContext` | — |
| 1. Context merge | `context_merge_service.py::ContextMergeService.merge` (`:79-186`) | RequestContext(+profile) → `MergedContext` | — |
| 2. Retrieval | `candidate_retrieval_service.py::get_candidates` (`:19-30`) | MergedContext → `list[Place]` ≤120 | **300 LIMIT → balance to 120** |
| 2b. Quality annotate | `route_builder_flow.py::_annotate_quality` (`:178-180`) | places → annotated | none (no drop) |
| 3. Hard filters | `hard_filters_service.py` → `route_filter_policy.py::filter_places` (`:28-41`) | annotated → kept | shrink (with strict/relaxed) |
| 4. Scoring | `scoring_service.py::ScoringService.score` (`:100-116`) | kept → `list[ScoredPlace]` sorted | none |
| 5. Assembly | `route_assembly_optimizer.py::assemble_route` (`:32-40`) | scored → `list[RoutePoint]` | shrink (`scored[:120]`, diversity, budget) |
| 6. Time ordering | `route_time_ordering_service.py::order` (`:14-21`) | points → reordered | none |
| 7. Time aware | `time_aware_service.py::apply` (`:24-77`) | points → annotated | none |
| 8. Budget fit | `route_budget_fit_service.py::fit` | route → trimmed/minimal route | shrink only |
| 9. Finalize | `route_finalize_service.py::finalize` (`:18-68`) | route → `FinalRoute` | none |

---

## 4. Candidate Loss Map

Where the place list shrinks (with whether it is traced per-place):

1. **SQL `LIMIT 300`** (`candidate_retrieval_service.py:58`) — drops places ranked 301+ by distance. **Silent** (no per-place trace).
2. **`balance_candidates_by_category(..., 120)`** (`:30`, `candidate_category_budget.py`) — round-robin to ≤120. **Silent.**
3. **Radius fallback** if `< 20` candidates (`:27-28`) → radius ×1.5 re-query (`:72`). **Not reflected in diagnostics.**
4. **Hard filters** (`route_filter_policy.py:35-41`): strict pool; if `< MIN_POOL_SIZE=15` (`hard_filters_service.py:13`) relax only `price_budget`. Per-reason counts traced, **per-place IDs not**.
5. **`scored[:120]`** assembly slice (`route_assembly_optimizer.py:36,39`) — only top 120 scored considered. **Silent.**
6. **Diversity pressure** (`route_diversity_policy.py`, `route_assembly_optimizer.py`): repeated categories are penalized/limited during assembly, while adaptive planning exposes expansion in trace.
7. **Budget trim** (`route_budget_fit_service.py:25-36`): tail points dropped when walk+visit exceeds `effective_time_budget_minutes`; first point kept even if over budget.

---

## 5. Scoring Review

`scoring_service.py::score` (`:100-116`). Weights `:152-159`, validation penalties `:65-68`, distance normalization `111_000.0` (`:215`). No shrink, no silent drop. Output sorted desc. Trace: `count`, `top3_scores` (`route_pipeline_trace.py:24-25`). → OK. REQUIRES VERIFICATION: weight tuning vs real catalog density (no fixture-based regression test on score ordering stability).

---

## 6. Filtering Review

Hard-filter reasons (`route_filter_reasons.py`): `explicit_place_exclude`, `status`, `no_coordinates`, `avoided_category`, `closed_now`, `unknown_hours_time_sensitive` (only when `route_time_mode=="now"`), `price_budget` (strict only).

- `closed_now` + `unknown_hours_time_sensitive` can aggressively shrink the pool in "now" mode for catalogs with sparse `opening_hours`. → TECHNICAL DEBT (data-dependent short routes).
- `ALL_FILTERED_WARNING` emitted if candidates existed but all filtered (`route_pipeline_warnings.py:27-31`). Good.
- Relaxation only drops `price_budget`; safety filters retained. → OK.

---

## 7. Assembly Review

`route_assembly_optimizer.py`. Caps:

```12:14:services/route_assembly_optimizer.py
MIN_BUDGET_UTILIZATION = 0.78
DEFAULT_MINUTES_PER_POINT = 24
MAX_TARGET_POINTS = 8
```

Target points: `max(2, min(MAX_TARGET_POINTS, max(from_context, by_budget)))` (`:210`). Relaxation order: relaxed categories → relaxed budget (+10%) (`:91-118`). Only `scored[:120]` considered (`:36,39`). Greedy selection + diversity + internal budget.

**Short-route root causes:** small pool after filters + diversity default cap of 2 + `effective_num_stops` capped at 6 (`merged_context.py:142`) but "ready" needs only `max(2, min(3, expected))` (`route_status_service.py:25-26`) → many routes legitimately land at 2–3 stops and are labeled `partial_route` when the pool is thin. → PARTIALLY IMPLEMENTED (works, but feels short).

Assembly trace is recorded **before** time ordering/time-aware (`route_builder_flow.py:89-92`), so `route_minutes` in the assembly trace stage predates final timing. → TECHNICAL DEBT (trace timing).

---

## 8. Correction / Replan Review

- User routes correction: `routers/user_routes.py` → `POST /v1/user-routes/correct` (remove/shorten/rebuild/avoid/extend). Tests: `test_user_route_correct_service.py`, `test_user_routes_flexible_new.py`.
- Replan: legacy `itinerary_replan_service` (separate engine). Test: `test_itinerary_replan_new.py`.
- `extend_route` supported in backend + frontend, but bot lacks a button (see File 04 TG-3). → PARTIALLY IMPLEMENTED.

---

## 9. Observability / Warnings Review

- Trace stages via `RoutePipelineTrace.add` / `timed_trace`: `context_merge`, `candidate_retrieval`, `quality_annotation`, `hard_filter`, `scoring`, `assembly`, `time_aware`, `budget_fit`. Logged as JSON to `city_go.route_pipeline` (`log_route_trace`).
- Warnings: `route_pipeline_warnings.py` (`NO_CANDIDATES`, `ALL_FILTERED_WARNING`, `NO_ROUTE_POINTS_WARNING`), `route_quality_warnings.py` (`SHORT_ROUTE_WARNING` `< max(2, expected//2)` `:29-30`, low diversity dominant ≥75% `:26`), `route_budget_fit_service.py` (`ROUTE_BUDGET_TRIMMED_WARNING`, `ROUTE_BUDGET_SINGLE_POINT_WARNING`).
- **Gaps:** no per-place drop log; radius fallback and balance-to-120 not surfaced; assembly trace timing predates final timing; `route_candidate_diagnostics.py` counts diverge from retrieval. → TECHNICAL DEBT.

---

## 10. Future Route Features Gap Analysis

| Feature | Status | Note |
|---|---|---|
| Route Constructor | FUTURE ROADMAP | manual point assembly not built |
| Active Route Session | FUTURE ROADMAP | no session/progress model |
| Live Route Editing | PARTIALLY IMPLEMENTED | correction exists; live editing does not |
| Route Recovery | FUTURE ROADMAP | no deviation detection |
| Smart Detours | FUTURE ROADMAP | none |

Not defects. Foundation (correction engine, time-aware) is reusable.

---

## 11. Route Engine Risks

| # | Risk | Class | Evidence |
|---|---|---|---|
| R1 | `is_route_eligible` not enforced in retrieval | REAL DEFECT | `candidate_retrieval_service.py:41-48` |
| R2 | Diagnostics counts ≠ retrieval (eligibility, scope, radius fallback, balance) | TECHNICAL DEBT | `route_candidate_diagnostics.py:24-27` |
| R3 | Test targets non-existent `_fallback_city_scope` | REAL DEFECT | `tests/test_candidate_retrieval_city_scope_fallback_new.py` |
| R4 | Silent caps chain (300→120→scored[:120]→diversity→trim) without per-place trace | TECHNICAL DEBT | retrieval + assembly |
| R5 | Short routes from thin pool + cap interactions | PARTIALLY IMPLEMENTED | `merged_context.py:142`, `route_diversity_policy.py:24` |
| R6 | Assembly trace timing predates final timing | TECHNICAL DEBT | `route_builder_flow.py:89-92` |
| R7 | No tests for diagnostics; no eligibility/retrieval parity test | TECHNICAL DEBT | tests/ grep |
| R8 | Duplicate `itinerary` engine | TECHNICAL DEBT | `routers/itinerary.py` |
| R9 | "now" mode over-filters on sparse opening_hours | TECHNICAL DEBT | `route_filter_reasons.py` |

---

## 12. Route Engine Stabilization Backlog

**P0**
- RE-1 (R1/R2): Enforce `is_route_eligible` in retrieval and make diagnostics use the same conditions as retrieval (incl. scope + radius fallback note). Files: `candidate_retrieval_service.py`, `route_candidate_diagnostics.py`. DoD: parity test (diagnostics count == retrieval count) + eligibility exclusion test. Size M.
- RE-2 (R3): Fix or delete `test_candidate_retrieval_city_scope_fallback_new.py` to match real `_fallback_expand_radius`. Files: that test. DoD: test asserts real behavior. Size S.

**P1**
- RE-3 (R4): Add per-place drop diagnostics (dropped IDs + reason + stage) to the trace; surface radius-fallback-used and balance-trim counts. Files: `route_pipeline_trace.py`, `candidate_retrieval_service.py`, `route_assembly_optimizer.py`. DoD: trace shows where each lost place dropped. Size M.
- RE-4 (R7): Add tests for `route_candidate_diagnostics.py` and a short-route regression fixture. Size M.
- RE-5 (R5): Make `effective_num_stops` cap and diversity defaults configurable per city/density; add observability for "pool too small". Files: `merged_context.py`, `route_diversity_policy.py`. Size M.

**P2**
- RE-6 (R6): Move assembly trace `route_minutes` capture to post-timing or add a final-timing stage. Size S.
- RE-7 (R9): In "now" mode, treat unknown hours as soft (warn) rather than hard-drop when pool is thin. Size M.

**P3**
- RE-8 (R8): Decide fate of legacy `itinerary` engine (converge or formally deprecate). Size L.

---

## 13. First Implementation Prompt

```
Implement RE-1 + RE-2 from docs/audits/05_route_engine_deep_audit.md (route eligibility enforcement + diagnostics parity + fix dead test).

Scope:
- services/candidate_retrieval_service.py: enforce is_route_eligible in _query_places
  (use public_route_place_conditions() or add _true_or_null(Place.is_route_eligible)); keep the scope filter.
- services/route_candidate_diagnostics.py: compute counts with the SAME conditions retrieval uses
  (eligibility + scope), and note radius-fallback as a separate field rather than implying a single count.
- tests/test_candidate_retrieval_city_scope_fallback_new.py: rewrite to test the real _fallback_expand_radius
  (there is no _fallback_city_scope in production code).

Constraints: do not change scoring weights, do not change assembly caps in this slice, do not touch the legacy itinerary engine.

Tests (suffix _new):
- published place with is_route_eligible=False excluded from candidates.
- diagnostics route-visible count == actual retrieval count for a fixture city (no radius fallback).
- radius fallback path is asserted via _fallback_expand_radius.

Docs: update docs/architecture/place_visibility.md route-eligibility note.

Analyze first, then implement. Report changed files, tests run, residual risks in one block.
```
