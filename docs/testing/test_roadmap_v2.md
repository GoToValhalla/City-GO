# City GO Test Roadmap v2

Date: 2026-07-02
Parent: CITYGO-149

## Goal

CI must protect the real product flows, not only compile code.

## Current baseline

- backend regression green;
- frontend tests green;
- Russian Allure scenarios 52%;
- backend overall coverage around 80%.

## Priority groups

1. Admin smoke for all tabs.
2. Route build golden scenarios.
3. Import idempotency and replay.
4. Publication state invariants.
5. Search input and filter stability.
6. Telegram Mini App route flow.
7. Projection stale/fresh behavior.
8. Prompt gate and cost budget.
9. Monitoring and alert smoke.

## Required scenarios

Route:

- enough places gives 3+ points;
- low data gives partial route with warnings;
- no candidates gives empty result with reason;
- unpublished and hidden places are excluded.

Admin:

- all tabs load;
- quality metrics are meaningful;
- review queue pagination works;
- bulk apply requires dry run;
- rollback requires reason and snapshot version.

Import:

- rerun is safe;
- failed payload is inspectable;
- replay uses same key;
- partial import does not change public state.

Publication:

- publish requires gate;
- snapshot is created;
- rollback restores prior snapshot.

## Targets

Phase A: backend overall 82%, Russian scenarios 60%.
Phase B: backend overall 86%, Russian scenarios 75%.
Phase C: backend overall 90%, Russian scenarios 90%.

## Definition of Done

Every new feature needs happy path, failure path, state invariant where needed, API contract where needed and UI regression where needed.
