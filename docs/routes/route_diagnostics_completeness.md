# Route Diagnostics Completeness (CITYGO-360)

Date: 2026-07-20. Read-only audit of existing diagnostics.
No new diagnostics framework. Public/internal boundary checked.

## 1. Diagnostic owners

| Surface | Owner | Audience |
|---|---|---|
| Pipeline stage trace | `services/route_pipeline_trace.py` → `FinalRoute.pipeline_trace` | backend / admin |
| Compact public trace | `compact_route_trace` / `route_debug_summary` | recommendations response |
| Full last-run debug | `get_last_route_debug` via `GET /admin/routes/debug-last` | admin only |
| Generation records | `route_generation_runs` + `route_generation_candidates` | admin / SQL |
| User-route public state | `user_route_mapper` + `sanitize_user_route_state` | public API |
| Preview failure | `routers/user_routes.py::_failed_preview` | public (sanitized) |
| Admin dry-run / draft | dry-run response + generation_run_id | admin |
| Admin eligibility / readiness | `routers/admin_route_eligibility.py` | admin |

## 2. Failure-mode → coverage matrix

| Failure mode | Localizable via | Gap? |
|---|---|---|
| Unpublished city → no candidates | retrieval counters + `no_route` status + generation run | No |
| Unpublished / invisible / service-only / non-eligible place | hard_filter reason_counts + public contract gates | No |
| Zero candidates | `failure_stage` / death_point in `route_debug_summary` | No |
| Budget trim / partial route | budget_fit stage + `partial_reason` + warnings | No |
| One-point never ready | canonical `route_status()` + finalize stage | No |
| Unknown / invalid status | status coherence invariants (eval dataset) | No |
| Preview mapping / timeout | sanitized `debug_trace` stage + status `preview_failed` | No |
| DB unavailable on user-routes | `_database_http_error` stable public code | No |
| Toggle / kill-switch block | feature-toggle guards (pre-pipeline) | Coarse: not always in pipeline_trace |
| Generation persist write fail | swallowed in record layer | Yes: silent; build still works |
| Admin dry-run no selected | dry-run counts + product_events | No |

Conclusion: every production route-build failure that reaches the
canonical pipeline can be localized with existing diagnostics. Remaining
gaps are coarse/pre-pipeline (toggles) or non-blocking persist failures,
not missing localization for user-visible route outcomes.

## 3. Public / internal boundary

| Path | Behavior | Verdict |
|---|---|---|
| Recommendations `_trace` | only with `X-Debug` | Correct |
| Recommendations `debug_trace` | compact only | Correct |
| Admin `debug-last` | full_trace for admins | Correct |
| User-routes `debug_trace` | mapper copies pipeline_trace; sanitizer must scrub secrets | Fixed in CITYGO-360 |
| Preview exception path | class name + fixed message only | Already correct |
| DB / state conflict HTTP | stable codes, no `str(exc)` leak | Already correct |

## 4. Path verification (this task)

### `services/admin_route_draft_pipeline.py::generate_admin_route_draft`

Verified correct. Flow: city 404 → dry-run → require selected places →
draft + points → warnings if fewer than 2 places → audit → serialize. Optional
`request.limit` truncates dry-run `selected_places` by design
(`AdminRouteDryRunService._split_candidates`); draft generation reuses
that list intentionally. No code change.

### `routers/admin_route_eligibility.py`

Verified correct. Admin auth on all endpoints; eligibility list and
readiness diagnostics delegate to existing services; forbidden-category
cleanup uses `reconcile_published_place_state` and soft-skips
`InvalidPublicationTransition` (fail-soft bulk). Unknown city → 404 on
diagnostics/readiness. No code change.
