# City GO — Import Discipline Stage 2

Date: 2026-07-02
Status: implementation baseline
Jira: CITYGO-125

## Goal

Stage 2 turns import into a controlled ingestion boundary.

Import may create observations, batches, checkpoints, dead letter items, conflicts and candidates. Import must not directly change product publication state.

## Entities

### ImportRun

Logical import execution.

Tracks:

- city;
- scope;
- provider;
- run type;
- status;
- checkpoint payload;
- counters;
- quality summary;
- timestamps;
- error summary.

### ImportBatch

One page/chunk/batch inside an ImportRun.

Tracks:

- import run;
- batch key;
- provider cursor;
- status;
- processed/created/matched/rejected/failed counts;
- checkpoint payload.

### ImportDeadLetterItem

Failed payload for inspection and replay.

Tracks:

- run/batch;
- source observation when available;
- payload hash/reference;
- error class/message;
- replay status;
- replay attempts.

### ImportConflictCandidate

Dedup/provider conflict candidate.

Tracks:

- source observation;
- matched place;
- conflict type;
- score;
- evidence payload;
- resolution status.

## Status lifecycles

ImportRun:

```text
queued -> running -> partial_success -> success -> failed -> retry_scheduled -> dead_lettered -> replayed
```

ImportBatch:

```text
pending -> processing -> completed -> failed -> dead_lettered -> replayed
```

DeadLetter:

```text
open -> replay_scheduled -> replayed -> ignored
```

Conflict:

```text
open -> auto_resolved -> manually_resolved -> rejected -> superseded
```

## Required rules

- raw payloads require deterministic idempotency key;
- batch failure does not automatically fail the city;
- failed/partial import does not unpublish city/place;
- source attribution is captured before normalization;
- conflicts are explicit and reviewable;
- replay uses the same idempotency contract.

## Stage 2 tests

Required:

- metadata contains Stage 2 tables;
- test DB creates Stage 2 tables;
- ImportRun has checkpoint/status/counter fields;
- ImportBatch has cursor/status/counter fields;
- ImportDeadLetterItem has replay/error payload fields;
- ImportConflictCandidate has evidence/score/status fields;
- failed/partial import cannot change public city/place state.

## Exit criteria

Stage 2 is complete when docs, Confluence, Jira, models and schema tests exist and CI is green.
