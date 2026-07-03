# CITYGO-171 · Data Quality Gate

The full product and implementation plan is documented in Confluence:

- `CITYGO-171 · P0 Data Quality Gate`
- Parent: `CITY GO Route Builder v2 Production Integration`

Implementation summary:

- Pause new route UI/session/constructor work until data quality gate is fixed.
- Create a single route eligibility policy.
- Route eligibility must use canonical category only.
- Unknown/null eligibility is fail-closed.
- Medical/service/transport/utility/generic OSM places must not be tourist route stops.
- Admin excluded/unknown route metrics must be truthful.
- Route assembly must not return large budget overflows as normal success.
- Production smoke must validate route content.
- Backend and UI automation must pass before the task is considered done.

Definition of done:

- Yerevan 120-minute quick route contains no medical/service/junk/generic OSM places.
- `Институт хирургии им. Микаеляна` never appears in tourist routes.
- `Место для прогулки OSM <id>` is not route eligible.
- Admin `Исключены из маршрутов` is not falsely zero.
- Route does not show `284/120` as normal success.
- UI tests confirm implementation matches the specification.

## Implemented repository contract

The single policy entrypoint is `services/route_eligibility_policy.py`.

- `evaluate_place_route_eligibility(place, context="tourist_walk")` computes the intrinsic route verdict used by recompute/publication workflows.
- `compile_route_eligible_sql_conditions(context="tourist_walk")` is the SQL gate used by retrieval and manual route draft search.
- Runtime retrieval still requires `is_route_eligible IS TRUE`; recompute/publication can turn safe places back on because the intrinsic verdict does not depend on the previous stored flag.
- Canonical category source is `Place.canonical_category` or `Category.code` through `category_ref`. Raw/display `Place.category` is not a policy source of truth.
- Unknown canonical category fails closed with `unknown_category`.
- Generic OSM placeholders fail closed with `generic_osm_placeholder`.

P0 hard exclusions for tourist walking routes include medical/healthcare, pharmacies, banks/ATMs, parking/fuel/toilets, police, transport stops, services/utilities, industrial/shelter/post office/vending/bench/waste/charging categories and generic OSM placeholder titles.

Photo and address are not P0 hard blockers. They remain admin/scoring/backlog signals. Technical or missing addresses must use user-facing fallbacks such as `адрес уточняется`.

## Admin operator overview

`/api/admin/overview` is an operator workflow panel, not a technical counter dump.
Every card must include:

- `queue_type`;
- `primary_action`;
- `short_hint`;
- `sample_endpoint`;
- `owner`;
- `is_human_actionable`;
- `mobile_priority`.

Card copy must be short Russian operator language. User-facing card fields must not expose internal words such as `published/catalog`, `route policy`, `canonical category`, `taxonomy`, `enrichment/policy`, `verification backlog`, `critical confidence`, `is_route_eligible`, `route_builder`, `backend`, `SQL`, `bucket`, `eligible` or `policy`.

The route cards are intentionally separated:

- `route_blockers` / `Проблемы маршрутов`: aggregate of published places that will not enter routes because of route flag, missing coordinates, service category or unknown category.
- `not_route_eligible` / `Отключены вручную`: only published places explicitly disabled from routes.
- `route_unknown` / `Неизвестные категории`: published places that need category assignment.
- `route_excluded` / `Сервисные точки`: published service POI that should stay out of tourist routes.

Each card with `sample_endpoint` must match `/admin/places/search` total exactly. The frontend renders `short_hint` and does not show legacy long `hint` when `short_hint` exists.

## Diagnostics and recompute

Read-only audit:

```bash
./scripts/audit_route_eligibility_drift.py
```

Dry-run recompute:

```bash
./scripts/recompute_route_eligibility.py --mode=dry-run --batch-size=500
```

Apply recompute:

```bash
./scripts/recompute_route_eligibility.py --mode=apply --confirm --batch-size=500
```

The apply mode only updates `is_route_eligible` and `route_exclusion_reason`.
It does not mass-unpublish places.

## Smoke behavior

Production smoke fails on hard-excluded route categories, generic OSM route titles, raw technical public warnings and 2x+ budget overflow without an honest weak/partial explanation.

User-facing route fields include `partial_reason`, `warnings`, `user_warnings`, `user_explanation` and `explanation`. Raw snake_case values in those fields must fail with an exact JSON path, for example `raw_technical_code_at_user_warnings[0].type`.

## 2026-07-03 follow-up

- `/cities/available` city selector counters are catalogue counters, not route-eligible counters.
- Public route controls must hide categories blocked by the route policy.
- Production smoke now enables route product smoke by default for Yerevan, 120 minutes, city center start.
- Manual smoke can leave `expected_sha` empty when checking only production availability.
