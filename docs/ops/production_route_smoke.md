# CITYGO-168 · Production Route Smoke Enabled

## Implemented

- `scripts/production_smoke.py` keeps route smoke behind explicit config:
  - CLI: `--route-smoke`;
  - env: `CITY_GO_ROUTE_SMOKE_ENABLED=true`.
- CLI/env execution defaults route smoke city to `yerevan` with city-center coordinates `40.1792, 44.4991`.
- Direct/programmatic `ProductionSmokeConfig(route_smoke_enabled=True)` requires explicit `route_city_id`; this prevents accidental silent smoke requests against an unspecified city in unit tests or custom callers.
- Route smoke checks:
  - route endpoint returns HTTP 200;
  - response is JSON object;
  - no raw traceback/internal error marker in response body;
  - route is not failed/empty;
  - route does not contain forbidden junk categories such as pharmacy, bus stop, bank, ATM, parking, fuel, toilet, utility/service/transport/health;
  - user-facing route fields do not expose raw technical warning codes;
  - smoke-local budget minimum is 2 points for the 120-minute smoke request;
  - honest `partial_route`/`weak` with reason is allowed, so data-density problems are visible without producing false deploy failures.

## Tests

- `tests/test_production_smoke_script.py` covers:
  - explicit city requirement for programmatic route smoke;
  - route response validation with the smoke-local 2-point minimum;
  - honest weak route accepted;
  - forbidden junk rejected;
  - raw technical user-facing warning code rejected.
- `tests/test_route_quality_product_fixes.py` covers product-level route quality behavior separately from smoke tolerance.

## Operational note

Production Deploy workflow was not changed in this pass. Route smoke remains opt-in through env/config and can be enabled safely after deploy config is confirmed.

When production route smoke is enabled in Actions, use these inputs/secrets/env values consistently:

- `CITY_GO_ROUTE_SMOKE_ENABLED=true`
- `CITY_GO_ROUTE_SMOKE_CITY_ID=<published city slug/id>`
- optional `CITY_GO_ROUTE_SMOKE_LAT` / `CITY_GO_ROUTE_SMOKE_LNG` when the default city center is not appropriate.
