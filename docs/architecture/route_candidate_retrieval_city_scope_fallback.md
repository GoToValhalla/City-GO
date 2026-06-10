# Route candidate retrieval

`services/candidate_retrieval_service.py` searches route candidates in this order:

1. selected radius;
2. expanded radius;
3. selected city without radius, only when `ctx.city_id` is set.

The last step keeps public route visibility, scope visibility, avoided places, avoided categories and distance ordering.

Tests: `tests/test_candidate_retrieval_city_scope_fallback_new.py`.
