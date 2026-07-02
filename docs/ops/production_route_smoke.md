# CITYGO-168 · Production Route Smoke Enabled

## Implemented

- `scripts/production_smoke.py` keeps route smoke behind explicit config:
  - CLI: `--route-smoke`;
  - env: `CITY_GO_ROUTE_SMOKE_ENABLED=true`.
- Default route smoke city is `yerevan` with city-center coordinates `40.1792, 44.4991`.
- Route smoke checks:
  - route endpoint returns HTTP 200;
  - response is JSON object;
  - no raw traceback/internal error marker in response body;
  - route is not failed/empty;
  - route does not contain forbidden junk categories such as pharmacy, bus stop, bank, ATM, parking, fuel, toilet, utility/service/transport/health;
  - user-facing route fields do not expose raw technical warning codes;
  - budget minimum is enforced, but honest `partial_route`/`weak` with reason is allowed.

## Tests

- `tests/test_route_quality_product_fixes.py` covers smoke validation for:
  - honest weak route accepted;
  - forbidden junk rejected;
  - raw technical user-facing warning code rejected.

## Operational note

Production Deploy workflow was not changed in this pass. Route smoke remains opt-in through env/config and can be enabled safely after deploy config is confirmed.
