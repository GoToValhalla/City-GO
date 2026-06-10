# MVP Release Checklist

## Required Gates

- Full tests pass: `.venv/bin/python -m pytest -q`.
- Backend quality gate passes: `.venv/bin/python scripts/backend_quality_gate.py`.
- Alembic applies from current DB state: `alembic upgrade head`.
- Backend starts and `scripts/release_smoke.sh` passes.
- Fresh backup exists and restore was tested.
- `scripts/check_place_coverage_gate.py` passes against `GET /place-coverage/zelenogradsk`.
- Telegram bot smoke passes: `/start`, route build, correction, unsupported city.
- UI Playwright smoke passes for route builder, warnings, nearby, mobile.

## Data Gates

- Total places: at least 80.
- Coordinates: at least 95%.
- Opening hours: at least 70%.
- Visit duration: at least 80%.
- Required backend categories present: coffee, food, walk, museum, bar, park.
  Product aliases: `museum` covers culture; `bar` covers evening.
- No `closed` or `temporarily_closed` places in generated routes.

Пороги gate можно переопределить через:
`COVERAGE_GATE_CITY_SLUG`, `COVERAGE_GATE_MIN_TOTAL_PLACES`,
`COVERAGE_GATE_MIN_COORDINATES_RATIO`, `COVERAGE_GATE_MIN_OPENING_HOURS_RATIO`,
`COVERAGE_GATE_MIN_VISIT_DURATION_RATIO`, `COVERAGE_GATE_REQUIRED_CATEGORIES`.

## Rollback

1. Stop deploy rollout.
2. Restore previous app version.
3. Restore DB from the latest verified backup if migration/data import caused the issue.
4. Run release smoke.
5. Record incident notes in `docs/change_history.md`.

## Release Decision

Ship only when all required gates pass. If a gate is skipped, write the reason and owner before release.
