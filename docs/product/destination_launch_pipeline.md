# City GO — Destination Launch Pipeline

Date: 2026-07-02
Status: implementation baseline
Jira: CITYGO-151

## Goal

Admin can launch a destination through an explicit controlled pipeline instead of manual scripts and implicit states.

## Flow

1. Create destination.
2. Start launch pipeline.
3. Run import.
4. Run enrichment.
5. Compute readiness.
6. Move to review.
7. Pass publication gate.
8. Publish destination.
9. Rebuild search and routing projections.
10. Mark route ready.

## Launch states

```text
created -> import_pending -> importing -> enrichment_pending -> enriching -> readiness_pending -> review_required -> publishable -> published -> projections_pending -> route_ready
```

Failure states:

```text
failed -> blocked -> archived
```

## Models

### DestinationLaunchState

Current launch status for one city/destination.

Required fields:

- city id;
- destination key;
- launch status;
- current step;
- actor;
- reason;
- readiness score;
- blocking reason;
- published flag;
- route ready flag.

### DestinationLaunchPipelineRun

One launch pipeline execution.

Required fields:

- city id;
- pipeline key;
- status;
- requested by;
- trigger source;
- started/finished timestamps;
- counters;
- error summary.

### DestinationLaunchStep

One step inside pipeline run.

Required fields:

- run id;
- step key;
- status;
- started/finished timestamps;
- input payload;
- output payload;
- error summary.

### DestinationReadinessSummary

Launch readiness snapshot.

Required fields:

- city id;
- pipeline run id;
- readiness score;
- place counters;
- photo/address/hours/description coverage;
- route eligibility;
- duplicate/conflict counters;
- blocking issues;
- publishable flag;
- route ready flag.

## Rules

- Failed launch cannot publish.
- Partial launch cannot publish without explicit readiness pass.
- Publish requires readiness summary.
- Route ready requires search and routing projections.
- Every state change has actor and reason.
- Launch pipeline does not silently unpublish existing public destination.
- Projection rebuild happens after publication, not before.

## Admin surface

Admin must see:

- current destination state;
- current pipeline run;
- each step status;
- readiness score;
- blocking issues;
- actions available now;
- last error summary;
- projection freshness.

## Tests

Required:

- metadata contains launch tables;
- test DB creates launch tables;
- launch state contract exists;
- pipeline run and step contracts exist;
- readiness summary contract exists;
- transition helper blocks illegal state jump;
- publish gate blocks failed or unready launch;
- route-ready gate requires projections.
