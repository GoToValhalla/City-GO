# CITYGO-162 · Route Quality Engine Hardening

## Implemented

- Useful route minimums are enforced in `services/route_quality_score.py`:
  - `<75` minutes: 1 point;
  - `75–119` minutes: 2 points;
  - `120+` minutes: 3 points.
- A route below the budget minimum is marked `weak` even when other score components look acceptable.
- Public warnings still come from `public_quality_warnings`; a short `120+` minute route is no longer presented as good.
- `services/route_diversity_policy.py` now centralizes category aliases and food-family limits for overview walks.

## Tests

- `tests/test_route_quality_product_fixes.py` covers:
  - 75/120 minute minimum thresholds;
  - weak quality for 2 points at 120 minutes;
  - food-family cap;
  - taxonomy alias normalization;
  - non-tourist category handling.

## Remaining

- The full route assembly optimizer was not rewritten in this pass. The production-safe layer makes weak routes honest first; further optimizer tuning can improve point selection quality.
