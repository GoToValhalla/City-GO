# City GO — Data Foundation Stage 1

Date: 2026-07-02
Status: implementation baseline
Jira: CITYGO-118

## Goal

Stage 1 implements the data foundation accepted in ADR-001..ADR-008. It separates raw data, versioned facts, AI candidates, review decisions, publication events and public snapshots.

## Entities

### SourceObservation

Append-only raw provider observation.

Owned by: Ingestion.

Required capabilities:

- provider identity;
- deterministic idempotency key;
- raw payload checksum/reference;
- source URL/license/attribution;
- city/scope/import batch relation;
- canonical place match relation;
- match/normalization status;
- confidence.

### PlaceFactVersion

Versioned fact for a place field and locale.

Owned by: Catalog + Moderation/Publication for status changes.

Lifecycle:

```text
candidate -> approved -> rejected -> superseded
```

Rules:

- import and AI may create candidate facts;
- only moderation/publication may approve/reject;
- updates append new rows instead of overwriting history.

### AiTaskRun

One AI invocation.

Owned by: AI Enrichment.

Tracks:

- task type;
- provider/model;
- prompt version/hash;
- input hash/reference;
- output;
- tokens/cost/latency;
- status/error.

### AiCandidate

AI-proposed candidate for a specific place field and locale.

Owned by: AI Enrichment.

Rules:

- not public by default;
- links to AiTaskRun;
- may link to PlaceFactVersion after approval;
- no direct public publication.

### ReviewDecision

Immutable moderation decision.

Owned by: Moderation.

Tracks:

- actor;
- target entity;
- decision;
- reason;
- previous value;
- new value;
- timestamp.

### PublicationEvent

Append-only publication transition.

Owned by: Publication.

Tracks:

- place/city;
- event type;
- previous state;
- next state;
- actor;
- reason;
- snapshot version;
- payload.

### PlaceSnapshot

Published/read-optimized projection.

Owned by: Publication.

Used by:

- public catalog;
- search;
- routing;
- Telegram/BFF.

## Compatibility path

The current `places` table remains the backward-compatible source for existing code during migration.

Path:

1. Introduce Stage 1 tables/models.
2. Add tests for metadata and test DB schema.
3. Backfill snapshots from current published places.
4. Move public reads to `PlaceSnapshot` behind compatibility adapters.
5. Move import/AI writes to `SourceObservation` and `AiCandidate`.
6. Deprecate legacy `places` fields after no active code uses them as source of truth.

## Ownership matrix

| Entity | Owner | Public read? | Append-only? |
|---|---|---:|---:|
| SourceObservation | Ingestion | No | Yes |
| PlaceFactVersion | Catalog/Publication | No hot path | Versioned append |
| AiTaskRun | AI | No | Yes |
| AiCandidate | AI | No | Versioned/statused |
| ReviewDecision | Moderation | No | Yes |
| PublicationEvent | Publication | No | Yes |
| PlaceSnapshot | Publication | Yes | Versioned projection |

## Stage 1 tests

Required:

- metadata contains Stage 1 tables;
- test DB creates Stage 1 tables;
- SourceObservation has idempotency/source attribution fields;
- PlaceFactVersion has locale/source/confidence/status;
- AiTaskRun has cost/latency/prompt fields;
- AiCandidate is candidate-only and links to AiTaskRun;
- ReviewDecision and PublicationEvent have actor/reason/state payload fields;
- PlaceSnapshot has snapshot version and public visibility flags.

## Exit criteria

Stage 1 is complete when docs, Confluence, Jira, models and schema tests exist and CI is green.
