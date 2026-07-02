# City GO — Destination Launch Pipeline v1

Date: 2026-07-02
Status: completed implementation contract
Jira: CITYGO-154
Confluence: CITY GO Launch Pipeline v1

## Goal

Destination Launch Pipeline v1 is the first implementation phase from Roadmap v2.

It defines the admin-driven flow for launching a city or future destination without direct database access and without changing code per destination.

## Main flow

```text
create destination
-> configure import
-> run import
-> run enrichment
-> review quality
-> approve publication
-> rebuild projections
-> run route smoke
-> go live
```

## Launch states

```text
created
-> import_pending
-> importing
-> enrichment_pending
-> enriching
-> readiness_pending
-> review_required
-> publishable
-> published
-> projections_pending
-> route_ready
-> live
```

Additional states:

- failed;
- blocked.

## Required checklist items

- import_scope_configured;
- import_completed;
- enrichment_completed;
- quality_gate_passed;
- review_queue_empty_or_accepted;
- publication_approved;
- projections_rebuilt;
- route_smoke_passed.

## Invariants

- launch state is separate from City publication state;
- import does not publish;
- enrichment does not publish;
- review does not publish by itself;
- publication requires quality gate;
- projection rebuild happens after publication;
- route smoke is required before live;
- live state requires route_ready, completed required checklist and passed route smoke;
- blocked state requires reason.

## Implemented model contract

Persistent launch tables:

- `destination_launch_states` — current launch state per destination/city;
- `destination_launch_pipeline_runs` — one launch execution;
- `destination_launch_steps` — per-step execution state;
- `destination_launch_checklist_items` — required readiness checklist used by admin/live gate;
- `destination_launch_events` — append-only timeline/audit contract;
- `destination_readiness_summaries` — readiness, coverage, publishability and projection readiness snapshot.

## Implemented service contract

`services/destination_launch_pipeline_service.py` owns deterministic guards:

- `assert_launch_transition_allowed()` blocks invalid state jumps;
- `calculate_launch_readiness_percent()` calculates required checklist completion;
- `missing_required_launch_items()` returns incomplete required live items in contract order;
- `assert_launch_can_go_live()` blocks live unless state is `route_ready`, all required items are completed and route smoke is `passed`;
- `assert_destination_publishable()` blocks publication unless readiness gate passes;
- `assert_destination_route_ready()` blocks route readiness unless publication, projections and route-eligible place count pass.

## Admin surface

Admin workspace must show:

- current launch state;
- checklist progress;
- readiness percent;
- last import run;
- last enrichment run;
- quality gate result;
- publication decision;
- projection rebuild status;
- route smoke status;
- next allowed actions;
- blocking reason.

## Commands

- CreateLaunchPipeline;
- ConfigureImport;
- StartImport;
- MarkImportReady;
- StartEnrichment;
- MarkEnrichmentReady;
- RequestReview;
- MarkReadyToPublish;
- StartPublishing;
- MarkPublished;
- MarkProjectionReady;
- MarkRouteSmokeReady;
- MarkLive;
- BlockLaunch.

## Events

- LaunchPipelineCreated;
- ImportConfigured;
- ImportStarted;
- ImportReady;
- EnrichmentStarted;
- EnrichmentReady;
- ReviewRequested;
- ReadyToPublish;
- PublishingStarted;
- Published;
- ProjectionReady;
- RouteSmokeReady;
- LaunchLive;
- LaunchBlocked.

## Test coverage

Covered in `tests/test_destination_launch_pipeline_contracts.py`:

- metadata contains all launch pipeline tables;
- test DB creates all launch pipeline tables;
- state/run/step/readiness/checklist/event table contracts;
- required checklist item order;
- readiness percent calculation;
- missing required item detection;
- full linear state transition path through `route_ready -> live`;
- invalid jump blocking;
- publish gate blocking;
- route-ready gate blocking;
- live gate blocking for wrong state, incomplete checklist and failed route smoke.

## Definition of Done

Pipeline v1 is complete when:

- state model exists;
- checklist model exists;
- event model exists;
- transition helper blocks invalid state jumps;
- readiness helper calculates progress;
- live helper requires all critical checklist items;
- docs exist;
- tests exist;
- CI is green.
