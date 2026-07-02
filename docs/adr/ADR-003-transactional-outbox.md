# ADR-003 — Transactional Outbox and Domain Events Baseline

Date: 2026-07-02
Status: Accepted
Jira: CITYGO-110

## Context

City GO needs cross-context reactions: import completion should trigger enrichment, approved facts should rebuild snapshots, published places should update search/routing projections. Doing direct DB write plus external message publish in one code path is unsafe without transactional guarantees.

## Decision

Adopt transactional outbox as the baseline event mechanism before introducing Kafka/Redpanda or another broker.

## Outbox contract

Required fields:

- id;
- event_type;
- aggregate_type;
- aggregate_id;
- payload_json;
- idempotency_key;
- status: pending / processing / published / failed / dead_lettered;
- attempts;
- next_attempt_at;
- created_at;
- published_at;
- last_error.

## Critical events

Durable and replayable:

- SourceObservationRecorded
- ImportBatchCompleted
- ImportRunCompleted
- PlaceCandidateCreated
- PlaceFactApproved
- PlaceFactRejected
- PlacePublished
- PlaceHidden
- PlaceRolledBack
- MediaCandidateApproved
- RouteGenerated

## Rules

- Business mutation and outbox insert happen in the same DB transaction.
- Event payloads are versioned.
- Consumers are idempotent.
- Events can be replayed to rebuild projections.
- No code may rely on direct synchronous cross-context side effects for critical state.

## Non-goals

This ADR does not require Kafka immediately. The first implementation can be a database outbox with polling worker.

## Consequences

Positive:

- consistent state and event emission;
- replayable projections;
- safer future broker migration;
- fewer hidden cross-context writes.

Negative:

- extra table and worker;
- event versioning discipline required;
- tests must validate emitted events.

## Testing requirements

- outbox row is created in same transaction as state change;
- rollback prevents outbox row;
- duplicate idempotency key does not emit duplicate event;
- projection rebuild can replay events;
- failed publish retries and then moves to dead letter state.
