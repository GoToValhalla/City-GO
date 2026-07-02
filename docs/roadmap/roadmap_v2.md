# City GO — Roadmap v2

Date: 2026-07-02
Parent: CITYGO-149

## Roadmap principle

Development order follows dependencies, not feature wish-list.

No new large feature starts without:

- product scenario;
- source of truth;
- read model;
- state transitions;
- event/audit;
- tests;
- monitoring signal.

## Phase 1 — Destination Launch Pipeline

Goal: admin can add and launch a destination without code changes.

Scope:

- destination creation;
- import scopes;
- launch state machine;
- import run visibility;
- quality readiness report;
- review queue entry points;
- publish gate.

Exit criteria:

- admin enters destination name;
- import pipeline starts;
- readiness is visible;
- destination can move to review;
- no public publication without gate.

## Phase 2 — Place Quality and Review Loop

Goal: reduce manual chaos and improve public quality.

Scope:

- quality dashboard v2;
- review queue v2;
- candidate evidence view;
- approve/reject/defer actions;
- duplicate/conflict handling;
- photo approval flow.

Exit criteria:

- admin sees what blocks publication;
- candidate approval writes review decision;
- no repeated enabled buttons after completed action;
- queue pagination and filters are stable.

## Phase 3 — Public Read Projections

Goal: move public/search/route reads away from legacy write tables.

Scope:

- PublishedPlaceSnapshot read path;
- SearchPlaceDocument;
- RoutingPlaceNode;
- projection rebuild jobs;
- stale projection warnings.

Exit criteria:

- public catalog uses projection;
- search uses projection;
- routing uses projection;
- stale projections are visible.

## Phase 4 — Route Builder v2

Goal: make routes useful and explainable.

Scope:

- Quick Build;
- Category Builder;
- Manual Build;
- Slot Builder;
- route warnings;
- replacement actions;
- route snapshot.

Exit criteria:

- enough data gives 3+ point route;
- empty/partial routes explain why;
- route excludes service noise;
- edit/rebuild works.

## Phase 5 — Telegram Mini App v2

Goal: phone-first product experience.

Scope:

- onboarding;
- city selection;
- route mode selection;
- route preview;
- active route;
- map/list sync;
- back navigation state preservation.

Exit criteria:

- user can build and start route from phone;
- UI is usable in Telegram;
- no white screen on search/input;
- route state survives navigation.

## Phase 6 — Admin Hardening

Goal: operate production without server/DB access.

Scope:

- admin watchdog;
- all-tab smoke;
- import monitor;
- audit log;
- kill switches;
- rollback UI;
- projection rebuild UI.

Exit criteria:

- admin 400/500 is alerted;
- dangerous operation has dry run;
- rollback is available;
- all critical tabs load in smoke.

## Phase 7 — Search and Recommendations

Goal: improve discovery and route relevance.

Scope:

- search filters;
- ranking breakdown;
- interests profile;
- category diversity;
- quality-aware recommendations.

Exit criteria:

- search is stable;
- results respect publication;
- recommendation reasons are explainable.

## Phase 8 — Analytics and Monitoring

Goal: know where product fails and why.

Scope:

- route failure analytics;
- city readiness trends;
- import health;
- enrichment costs;
- admin operation metrics;
- alert routing.

Exit criteria:

- route empty spike visible;
- import stuck visible;
- AI cost visible;
- admin failures visible.

## Phase 9 — Growth Experiments

Goal: test monetization and partner paths only after route value is stable.

Scope:

- premium route ideas;
- partner content rules;
- city packs;
- personalized recommendations.

Exit criteria:

- paid/partner content cannot bypass quality gates;
- experiments are feature-flagged;
- analytics can measure value.

## Immediate next implementation recommendation

Start Phase 1: Destination Launch Pipeline.

Reason:

- it directly supports scaling cities;
- it uses all architecture stages already created;
- it gives admin a complete operational flow;
- it will expose remaining data quality gaps quickly.
