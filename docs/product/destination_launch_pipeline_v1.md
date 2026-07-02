# City GO — Destination Launch Pipeline v1

Date: 2026-07-02
Status: implementation baseline
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
draft
-> import_configured
-> importing
-> import_ready
-> enriching
-> enrichment_ready
-> review_required
-> ready_to_publish
-> publishing
-> published
-> projection_ready
-> route_smoke_ready
-> live
```

Additional states:

- blocked;
- paused;
- cancelled;
- archived.

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
- blocked state requires reason.

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
- BlockLaunch;
- PauseLaunch;
- CancelLaunch.

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
- LaunchBlocked;
- LaunchPaused;
- LaunchCancelled.

## Definition of Done

Pipeline v1 is complete when:

- state model exists;
- checklist model exists;
- transition helper blocks invalid state jumps;
- readiness helper calculates progress;
- live helper requires all critical checklist items;
- docs exist;
- tests exist;
- CI is green.
