# City GO — Target Architecture Blueprint

Дата: 2026-07-02  
Источник: internal project context + консультации Gemini, Grok, Claude.  
Статус: baseline для дальнейших архитектурных решений.

## 0. Executive verdict

City GO нельзя дальше развивать как обычный CRUD-продукт вокруг одной таблицы `places` и набора admin endpoints. Реальный продукт состоит минимум из пяти систем:

1. Data ingestion / ETL platform.
2. Moderation and publication platform.
3. AI orchestration platform.
4. Search / recommendation platform.
5. Consumer route-planning app.

Главная архитектурная ошибка: смешение raw source data, AI-derived candidates, verified/master facts и public published view в одном mutable `Place`/`City` контуре.

Новая архитектура должна быть построена вокруг:

- strict bounded contexts;
- source-of-truth separation;
- fact versioning;
- read projections;
- outbox/events;
- async import/AI/media workloads;
- explicit state machines;
- regression/golden datasets.

## 1. What we accept from external reviews

### Accepted immediately

1. `Place` must be split conceptually into raw observations, master facts and published projections.
2. Import, AI enrichment, publication, search, routing and user API must not share mutable state casually.
3. AI must not write directly to public catalog state.
4. Publication must be event/audit driven and rollbackable.
5. Ingestion must be idempotent, checkpointable and replayable.
6. Search, routing and recommendation read from projections, not raw/master write tables.
7. Outbox pattern is required before introducing a real broker.
8. Modular monolith is acceptable now, but only with hard module/schema boundaries.
9. AI/prompt regression tests are mandatory before scaling enrichment.
10. Admin platform is core product, not a side panel.

### Accepted later, not immediate

These are directionally correct, but not day-one mandatory:

- Kafka/Redpanda cluster.
- Temporal as required orchestrator.
- Qdrant/Milvus as required vector database.
- OpenSearch as required search engine.
- Full microservices decomposition.
- ClickHouse/data lake for all telemetry.
- Learning-to-rank models.
- Full chaos/mutation/visual regression platform.

The near-term target is a modular monolith with internal contracts, schema separation and outbox. External services are introduced only when scale or failure mode requires extraction.

## 2. Bounded contexts

### 2.1 Catalog context

Owns canonical city/place identity and stable geometry.

Responsibilities:

- city identity;
- place identity;
- stable geometry;
- canonical references;
- master approved facts.

Must not own:

- import provider raw payloads;
- AI run history;
- Telegram UI state;
- search index logic;
- route generation logic;
- admin session/auth logic.

### 2.2 Ingestion context

Owns raw provider data and import lifecycle.

Responsibilities:

- `ImportRun`;
- `ImportBatch`;
- `SourceObservation`;
- provider cursors/checkpoints;
- idempotency keys;
- DLQ/replay;
- source license/attribution.

Must not directly publish places.

### 2.3 AI enrichment context

Owns AI tasks and candidates.

Responsibilities:

- `PromptVersion`;
- `AiTaskRun`;
- `AiCandidate`;
- model routing;
- confidence scoring;
- hallucination checks;
- cost tracking;
- golden dataset evaluation.

Must not directly mutate approved catalog facts or public projections.

### 2.4 Moderation and publication context

Owns review decisions and public state transitions.

Responsibilities:

- manual review queues;
- AI candidate approval/rejection;
- `ReviewDecision`;
- `PublicationEvent`;
- publish/hide/archive/rollback;
- quality gates;
- snapshot projection triggering.

Only this context may approve facts into public visibility.

### 2.5 Search and discovery context

Owns rebuildable search projections.

Responsibilities:

- FTS/semantic/geo indexes;
- autocomplete;
- facets;
- ranking metadata;
- zero-result metrics.

Search is never source of truth.

### 2.6 Routing context

Owns route generation and route artifacts.

Responsibilities:

- route generation requests;
- immutable route snapshots;
- route cache;
- route quality metrics;
- integration with OSRM/Valhalla/GraphHopper later.

Routing reads from published place snapshots.

### 2.7 Recommendation and personalization context

Owns user preference signals and ranking features.

Responsibilities:

- user preferences;
- interaction events;
- feature store;
- embeddings;
- feedback loops;
- ranking experiments.

Must not mutate catalog facts.

### 2.8 Media context

Owns photo ingestion, candidates, moderation, derivatives and CDN metadata.

Responsibilities:

- raw photo candidates;
- media rights/source attribution;
- moderation status;
- derivatives;
- public media projection.

### 2.9 Identity and access context

Owns users, admins, roles and permissions.

Must not leak into catalog models.

### 2.10 Client/BFF context

Owns Telegram Mini App shape and client-specific payloads.

Must not be the source of truth for catalog/publication/routing.

## 3. Target domain model

### 3.1 Current model problem

A single `Place` table with fields like `address`, `description`, `quality_score`, `publication_status`, `is_published`, `image_url`, `address_confidence`, `verification_status` is doing too much.

It mixes:

- raw imported facts;
- AI candidates;
- human-approved facts;
- quality signals;
- publication state;
- route/search visibility;
- media state.

This is acceptable for prototype but not for scale.

### 3.2 Target entities

#### Place

Stable identity only:

- id;
- city_id;
- stable canonical slug;
- geometry;
- created_at;
- archived_at/status.

#### SourceObservation

Append-only raw provider payload:

- provider;
- provider object id;
- import run/batch;
- raw payload/checksum;
- source license;
- observed_at;
- city scope.

#### PlaceFactVersion

Versioned fact row:

- place_id;
- field_name;
- locale;
- value_json;
- source type: source provider / AI / human;
- source reference;
- confidence;
- status: candidate / approved / rejected / superseded;
- created_at;
- superseded_by.

#### AiTaskRun

One AI invocation:

- task_type;
- model;
- prompt version;
- input hash;
- output;
- token cost;
- latency;
- status;
- error;
- created_at.

#### AiCandidate

AI-proposed fact candidate:

- place_id;
- ai_task_run_id;
- target field;
- proposed value;
- confidence;
- validation results;
- review status.

#### ReviewDecision

Immutable approval/rejection/edit decision:

- reviewer;
- target entity/field;
- decision;
- reason;
- old value;
- new value;
- created_at.

#### PublicationEvent

Append-only state transition:

- place_id/city_id;
- event type;
- previous state;
- next state;
- actor;
- reason;
- snapshot version;
- created_at.

#### PlaceSnapshot / PublishedPlace

Read-optimized public view:

- place_id;
- city_id;
- approved current fields;
- route/search/catalog flags;
- quality summary;
- media summary;
- snapshot_version;
- updated_at.

Search, routing, Telegram and public APIs should read this projection.

## 4. State machines

### 4.1 City lifecycle

```text
prospecting
  -> importing
  -> enrichment
  -> review_required
  -> published
  -> maintenance
  -> hidden
  -> archived
```

Import status does not equal product status.

### 4.2 Import lifecycle

```text
queued
  -> running
  -> partial_success
  -> success
  -> failed
  -> retry_scheduled
  -> dead_lettered
  -> replayed
```

Failed/partial import must never unpublish a city.

### 4.3 Fact lifecycle

```text
candidate
  -> approved
  -> rejected
  -> superseded
```

AI creates candidates, not approved facts.

### 4.4 Place publication lifecycle

```text
draft
  -> auto_backlog
  -> ai_review
  -> manual_review
  -> approved
  -> published
  -> hidden
  -> archived
  -> rollback_to_previous_snapshot
```

### 4.5 Manual review lifecycle

```text
open
  -> approved
  -> rejected
  -> deferred
  -> escalated
  -> closed
```

Manual review is not the same as low confidence backlog.

## 5. Data architecture

### 5.1 Near-term storage

Use PostgreSQL/PostGIS as the system of record, but split schemas logically:

```text
catalog
ingestion
ai
moderation
publication
search_meta
routing
recs
identity
media
ops
```

If physical schema split is too disruptive immediately, start with module-level boundaries and migration plan to schemas.

### 5.2 Index rules

Required:

- every FK indexed;
- `(city_id, status)` composite indexes on hot queries;
- GiST/SP-GiST indexes on geometry;
- partial indexes for published/visible/searchable records;
- unique idempotency keys for provider payloads;
- unique `(place_id, image_url)` for photo candidates;
- import job index `(city_id, created_at desc, id desc)`.

### 5.3 Projection strategy

Hot reads should target projections:

- `PlaceSnapshot` for public catalog;
- search projection for FTS/autocomplete;
- route projection for route eligibility;
- admin overview aggregates/materialized summaries.

### 5.4 Later storage

Introduce when metrics demand it:

- Redis for hot cache and rate limits;
- OpenSearch for high-QPS/faceted search;
- pgvector first, Qdrant later if semantic workloads outgrow Postgres;
- object storage for raw payloads/photos/old AI runs;
- ClickHouse or similar for high-volume analytics.

## 6. Event and outbox architecture

### 6.1 Immediate decision

Implement transactional outbox before Kafka/Redpanda.

Reason: every important cross-context mutation must write state and event atomically.

### 6.2 Critical events

Must be durable and replayable:

```text
SourceObservationRecorded
ImportBatchCompleted
ImportRunCompleted
PlaceCandidateCreated
PlaceFactApproved
PlaceFactRejected
PlacePublished
PlaceHidden
PlaceRolledBack
MediaCandidateApproved
RouteGenerated
```

### 6.3 Best-effort events

Can be lower durability:

```text
SearchViewed
RoutePreviewOpened
RecommendationClicked
AdminDashboardViewed
```

### 6.4 Outbox rule

Do not update DB and publish external message in the same execution block without outbox.

## 7. Import architecture

### 7.1 Target pipeline

```text
ImportRun created
  -> provider fetch pages into ImportBatch
  -> write SourceObservation append-only
  -> exact idempotency check
  -> fuzzy geo/name/domain conflict detection
  -> create candidate facts
  -> quality scoring
  -> enqueue AI enrichment only if needed
  -> route to auto publish / auto backlog / manual review
```

### 7.2 Required properties

- idempotent;
- checkpointable;
- resumable;
- batch-committed;
- DLQ-backed;
- replayable;
- city-scoped;
- source-attributed.

### 7.3 Immediate code direction

Stop adding import logic that directly mutates publication state. Import may create source observations and candidates only.

## 8. AI architecture

### 8.1 Rule

AI never writes directly to catalog approved facts or public snapshots.

AI writes:

- `AiTaskRun`;
- `AiCandidate`;
- validation output;
- confidence;
- cost metrics.

### 8.2 Pipelines

Separate task types:

- description extraction/generation;
- address normalization;
- opening hours extraction;
- category classification;
- photo validation/tagging;
- duplicate detection;
- conflict resolution;
- moderation classification;
- quality scoring;
- ranking feature extraction.

### 8.3 Prompt governance

Required:

- prompt versioning;
- golden datasets;
- regression gate per prompt type;
- cost budgets per task type;
- human override rate dashboard;
- model fallback/routing.

## 9. Publication architecture

### 9.1 Source of truth

Published truth is `PlaceSnapshot`/published projection built only from approved facts and publication events.

### 9.2 Quality gates

Publication gates should be named and auditable:

- required field completeness;
- geometry sanity;
- duplicate/conflict checks;
- category eligibility;
- source confidence;
- AI validation result;
- policy safety checks.

### 9.3 Rollback

Rollback appends `PlaceRolledBack` and restores previous snapshot version. No manual SQL resets.

## 10. Search and recommendation

### 10.1 Near-term

- Postgres FTS/trigram;
- PostGIS filters;
- explainable scoring;
- route/search eligibility flags from published snapshot.

### 10.2 Later

- OpenSearch for high-QPS/facets;
- pgvector/Qdrant for semantic recall;
- feature store;
- learning-to-rank only after real user behavior volume exists.

## 11. Routing architecture

### 11.1 Rule

Do not hand-roll low-level routing graph algorithms long-term.

Use OSRM/Valhalla/GraphHopper for physical graph and matrix travel times.

### 11.2 Split

Offline:

- city walking graph build;
- popular place distance matrices;
- route eligibility projection.

Online:

- candidate selection;
- constraint scoring;
- ordering over precomputed/matrix data;
- route snapshot creation.

## 12. Admin architecture

Admin is core product.

Required panels:

- import health;
- DLQ/replay;
- publication funnel;
- manual review queues;
- auto backlog;
- AI cost and quality;
- city readiness;
- place quality;
- search zero results;
- route generation health;
- audit log;
- kill switches.

Required actions:

- async bulk operations;
- dry-run/apply workflows;
- rollback;
- provider freeze;
- AI task freeze;
- city publish/unpublish;
- snapshot rebuild.

## 13. Telegram Mini App / Client architecture

Telegram is one client, not the architecture.

Required:

- BFF layer;
- stable versioned APIs;
- delta sync for places/routes;
- local cache for current city/recent routes;
- lightweight map payloads;
- no admin business logic in bot handlers.

## 14. Testing architecture

### 14.1 Immediate mandatory tests

- source-of-truth chain guards;
- publication state invariants;
- import idempotency/resume;
- AI prompt regression/golden sets;
- migration contract tests;
- query-budget tests;
- repair dry-run/apply tests;
- outbox event contract tests;
- search/routing projection rebuild tests.

### 14.2 Test architecture decision

Split DB tests:

- metadata-only unit/model tests;
- Alembic-created integration/API tests.

Default should not silently create published happy-path data for negative-state tests. Explicit fixtures already exist and must be expanded.

## 15. Security and compliance

Required early:

- separate admin auth path;
- RBAC;
- admin audit trail;
- rate limits for expensive endpoints;
- prompt injection guardrails;
- source poisoning checks;
- PII/location retention policy;
- right-to-erasure design;
- source license/attribution tracking.

## 16. Cost architecture

Primary future cost risks:

1. AI enrichment backfill.
2. Photo storage and derivatives.
3. Vector embeddings/re-embedding.
4. Search cluster overprovisioning.
5. Map tile usage.
6. Route generation CPU.

Required:

- hard AI task budgets;
- per-city/per-task quotas;
- semantic/prompt caching;
- photo deduplication;
- derivative generation;
- model routing by cost/quality.

## 17. Decisions required before further feature work

Critical decisions:

1. Adopt RawObservation / FactVersion / PublishedSnapshot model.
2. Define schema-per-bounded-context target.
3. Adopt transactional outbox.
4. Decide routing engine path: OSRM vs Valhalla vs GraphHopper.
5. Decide i18n model for facts.
6. Decide prompt versioning and golden dataset structure.
7. Decide admin review roles and authority.
8. Decide source attribution/licensing model.

## 18. Roadmap

### Phase 0 — Architecture freeze and ADRs

Deliverables:

- ADR: RawObservation / FactVersion / Snapshot.
- ADR: Modular monolith with schema boundaries.
- ADR: Transactional outbox.
- ADR: AI candidates never direct-write catalog.
- ADR: Routing engine choice.
- ADR: i18n fact model.

### Phase 1 — Data foundation

Deliverables:

- new tables for SourceObservation, PlaceFactVersion, AiTaskRun, AiCandidate, ReviewDecision, PublicationEvent, PlaceSnapshot;
- compatibility layer from current `places`;
- projection builder;
- migration tests.

### Phase 2 — Import discipline

Deliverables:

- ImportRun / ImportBatch;
- idempotency keys;
- DLQ;
- checkpoint/resume;
- source attribution;
- conflict candidates.

### Phase 3 — AI discipline

Deliverables:

- PromptVersion;
- task-specific AI pipelines;
- golden datasets;
- cost budgets;
- candidate review flow.

### Phase 4 — Publication and admin

Deliverables:

- publication state machine;
- quality gates;
- rollback;
- bulk review;
- backlog separation;
- audit everywhere.

### Phase 5 — Search/routing projections

Deliverables:

- PlaceSnapshot read APIs;
- search projection;
- route eligibility projection;
- route cache invalidation by events.

### Phase 6 — Scale services only when needed

Extract first:

1. AI enrichment service.
2. Media service.
3. Search service.
4. Routing service.

Do not split Catalog/Publication prematurely.

## 19. Immediate code actions

1. Stop adding new fields to `Place` for AI/publication/quality without deciding target fact model.
2. Add ADRs from Phase 0.
3. Add `SourceObservation` and `PlaceFactVersion` design docs before migrations.
4. Add outbox table and event contract docs.
5. Add golden dataset structure for AI tasks.
6. Add import idempotency and checkpoint design.
7. Add projection builder design for `PlaceSnapshot`.
8. Mark old direct publication/import scripts as legacy unless they follow dry-run/apply/audit.

## 20. Priority risk list

### Critical

- single mutable `Place` as raw/master/published/AI state;
- no fact versioning;
- no outbox/event consistency;
- AI direct catalog writes;
- import/publication state mixing.

### High

- no prompt versioning/golden tests;
- weak admin/review throughput;
- no i18n fact model;
- no source attribution/licensing model;
- no routing engine decision.

### Medium

- no vector/search migration trigger;
- weak query-budget coverage;
- default happy-path fixtures still exist;
- taxonomy governance not formalized.

### Low

- full microservices not needed yet;
- advanced ML ranking not needed yet;
- chaos/mutation/visual regression can wait until foundation is stable.

## 21. Non-negotiable rule

Every future feature must state which context it belongs to and which source-of-truth chain it uses:

```text
client/API -> context module -> source-of-truth table/projection -> event/audit -> tests
```

If this chain is unclear, the feature must not be implemented.
