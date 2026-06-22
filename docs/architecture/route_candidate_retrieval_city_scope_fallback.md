# Route candidate retrieval

`services/candidate_retrieval_service.py` searches route candidates in this order:

1. selected radius;
2. expanded radius;
3. selected city without radius, only when `ctx.city_id` is set.

The last step keeps public route visibility, scope visibility, avoided places, avoided categories and distance ordering.

If the request start point is far outside the selected city, retrieval may replace
`ctx.location` with `City.center_lat/center_lng` and records the original location,
fallback reason and distance in debug trace. This fallback is best-effort: tests
may pass lightweight fake DB objects, so inability to read `City` must degrade to
normal retrieval instead of crashing the route.

Tests:
- `tests/test_candidate_retrieval_city_scope_fallback_new.py`
- `tests/test_candidate_retrieval_city_wide_fallback_new.py`
- `tests/test_route_location_fallback_new.py`
