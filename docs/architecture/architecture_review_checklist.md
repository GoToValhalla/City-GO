# City GO — Architecture Review Checklist

Date: 2026-07-02
Status: Accepted
Jira: CITYGO-116

Every future feature, bugfix or refactor that touches product state must answer this checklist before implementation.

## 1. Bounded context

Which context owns this change?

- Catalog
- Ingestion
- AI Enrichment
- Moderation and Publication
- Search and Discovery
- Routing
- Recommendation and Personalization
- Media
- Identity and Access
- Client/BFF
- Ops/Admin

If no clear owner exists, stop and create/update ADR.

## 2. Source of truth

State the exact source-of-truth chain:

```text
client/API -> context module -> source-of-truth table/projection -> event/audit -> tests
```

## 3. Write path

Which tables/entities are written?

- Does this write raw data?
- Does this write candidate facts?
- Does this approve facts?
- Does this publish snapshots?
- Does this emit events?

Forbidden without explicit ADR:

- import/enrichment writing published state;
- AI writing approved/public facts;
- Telegram handler writing catalog/publication state directly;
- read endpoint changing product state.

## 4. Read path

Which projection/read model is used?

- Public API should read published snapshot.
- Search should read search projection.
- Routing should read route eligibility projection.
- Admin may read operational state, but must label it clearly.

## 5. State machine impact

Which state machine changes?

- City lifecycle
- Import lifecycle
- Fact lifecycle
- Publication lifecycle
- Manual review lifecycle
- AI task lifecycle
- Media lifecycle
- Route lifecycle

If states are added or renamed, update docs and tests.

## 6. Event/audit impact

Does this create a domain event?

- If yes: add outbox event contract.
- If destructive: add audit actor/reason.
- If projection-changing: add rebuild/invalidation path.

## 7. Migration impact

- Does it add a table/column/index?
- Is it backward compatible?
- Is there a rollback path?
- Are migration contract tests needed?

## 8. Test impact

Required tests to consider:

- unit;
- integration;
- API contract;
- migration contract;
- state invariant;
- query budget;
- regression;
- AI/prompt golden dataset;
- projection rebuild.

## 9. Documentation impact

Update one or more:

- ADR;
- state registry;
- legacy register;
- API contract;
- runbook;
- architecture blueprint.

## 10. Release and monitoring

- Feature flag needed?
- Backfill needed?
- Admin visibility needed?
- Alert/metric needed?
- Dry-run/apply needed?

## Approval rule

If a change touches publication, import, AI candidates, public snapshots or destructive admin actions and this checklist is not answered, the change is not ready.
