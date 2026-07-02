# ADR-001 — Data Model Split: RawObservation / FactVersion / PublishedSnapshot

Date: 2026-07-02
Status: Accepted
Jira: CITYGO-108

## Context

Current `Place` combines several different concepts:

- raw imported provider data;
- human-approved catalog facts;
- AI-generated candidates;
- quality signals;
- publication state;
- search/route/catalog visibility;
- media shortcuts.

This makes import, AI enrichment, publication, search and routing mutate the same row for different reasons. The result is fragile state coupling: import or reconciliation can accidentally affect published cities/places.

## Decision

City GO adopts a three-layer model:

1. `SourceObservation` — append-only raw provider observation.
2. `PlaceFactVersion` — versioned candidate/approved/rejected/superseded fact.
3. `PlaceSnapshot` / `PublishedPlace` — read-optimized public projection built only from approved facts and publication events.

`Place` becomes stable identity and geometry, not a dumping ground for every operational/public/AI field.

## Target concepts

### SourceObservation

Stores raw provider data exactly as received.

Required fields:

- id;
- provider;
- provider_object_id;
- import_run_id;
- import_batch_id;
- city_id;
- raw_payload_json or payload_reference;
- payload_checksum;
- source_license;
- attribution;
- observed_at;
- created_at.

Rules:

- append-only;
- never used directly by public API;
- can be replayed;
- has deterministic idempotency key.

### PlaceFactVersion

Stores proposed or approved facts.

Required fields:

- id;
- place_id;
- field_name;
- locale;
- value_json;
- source_type: provider / ai / human / system;
- source_ref;
- confidence;
- status: candidate / approved / rejected / superseded;
- created_by;
- created_at;
- superseded_by.

Rules:

- AI and import create candidates;
- only moderation/publication can approve;
- updates append new versions instead of overwriting history.

### PlaceSnapshot / PublishedPlace

Stores public read model.

Required fields:

- place_id;
- city_id;
- snapshot_version;
- approved public fields;
- catalog/search/route visibility flags;
- quality summary;
- media summary;
- built_from_event_id;
- updated_at.

Rules:

- search/routing/public APIs read snapshots;
- snapshots are rebuildable;
- rollback restores previous snapshot version through event append, not manual SQL.

## Consequences

Positive:

- raw data, AI candidates and public catalog are separated;
- publication rollback becomes deterministic;
- source attribution becomes traceable;
- AI hallucinations cannot directly poison public catalog;
- import failures cannot unpublish product state.

Negative:

- more tables and migration complexity;
- existing code needs compatibility layer;
- public API migration must be staged.

## Migration path

1. Keep current `places` as compatibility source.
2. Add new tables without removing old fields.
3. Backfill `PlaceSnapshot` from current published places.
4. Change public read APIs to prefer snapshot.
5. Change import/AI to create observations/candidates.
6. Gradually stop writing AI/publication/quality data into `places`.
7. Mark old fields as legacy compatibility.

## Non-negotiable rule

No new AI/publication/quality fields may be added to `Place` without explicitly proving why they do not belong to `SourceObservation`, `PlaceFactVersion`, `AiCandidate`, `PublicationEvent` or `PlaceSnapshot`.
