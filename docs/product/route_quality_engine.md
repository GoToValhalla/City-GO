# CITYGO-162 · Route Quality Engine Hardening

## Implemented

- Useful route minimums are enforced in `services/route_quality_score.py`:
  - `<75` minutes: 1 point;
  - `75–149` minutes: 2 points;
  - `150+` minutes: 3 points.
- Product quality still treats long sparse routes honestly:
  - routes below `minimum_points_for_budget` are marked `weak`;
  - routes with `120+` minute budget and fewer than 3 points are also marked `weak`, even though the generic minimum threshold for `120–149` minutes remains 2 points.
- Public warnings still come from `public_quality_warnings`:
  - very short budget shortages are reported as `route_short_due_to_time_budget`;
  - long/sparse route shortages are reported as `route_short_due_to_low_place_density`.
- `services.route_budget_fit_service.RouteBudgetFitService` uses the same minimum thresholds, so a 240-minute route with only 2 points is treated as low place density, not as a tight budget.
- `services/route_diversity_policy.py` centralizes category aliases and food-family limits for overview walks.

## Tests

- `tests/test_route_assembly_service.py` covers the canonical minimum thresholds: 15/74 -> 1, 75/149 -> 2, 150 -> 3.
- `tests/test_route_budget_fit_service.py` covers sparse long routes returning `route_short_due_to_low_place_density`.
- `tests/test_route_quality_product_fixes.py` covers:
  - weak quality for 2 points at 120 minutes;
  - public low-density warning for long sparse routes;
  - food-family cap;
  - taxonomy alias normalization;
  - non-tourist category handling.

## CI stabilization note

CI #2032 exposed a threshold conflict introduced during smoke hardening. The resolved contract is:

- Product quality threshold: 150+ minutes requires 3 points.
- 120+ minute sparse routes remain `weak` through the long-route quality guard.
- Production smoke keeps a local 2-point minimum for post-deploy tolerance and accepts honest `partial_route`/`weak` responses when the payload explains the shortage.

## CITYGO-171 note

CITYGO-171 is now the blocking prerequisite for further route UX expansion. See `docs/product/citygo_171_data_quality_gate.md`.

CITYGO-171 implementation adds the semantic data quality gate:

- route candidate SQL and Python validation share `services/route_eligibility_policy.py`;
- tourist walking routes use canonical category only (`canonical_category` or `Category.code`);
- raw/display category names are UI-only and cannot make a place route-safe;
- medical/service/transport/utility/generic OSM placeholders are hard-excluded;
- route retrieval may widen radius/geography but must not weaken the hard data-quality gate;
- manual add/replace uses the same SQL gate;
- emergency route backfill cannot add extra points when cumulative time would exceed the requested budget;
- production smoke rejects junk route points and 2x+ budget overflow unless the response is explicitly weak/partial with a user-facing explanation.

Photo and address remain quality/scoring/admin signals, not P0 hard blockers.

## Remaining

- The full route assembly optimizer was not rewritten in this pass. The production-safe layer makes weak routes honest first; further optimizer tuning can improve point selection quality.
- Continue route UI/session/constructor work only after CITYGO-171 data quality gate is verified.
