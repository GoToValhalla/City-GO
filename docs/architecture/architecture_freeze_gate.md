# City GO — Architecture Freeze Gate

Date: 2026-07-02
Status: Accepted
Jira: CITYGO-117

## Purpose

The freeze gate prevents new feature work from increasing architectural debt before foundational decisions are fixed.

## Gate requirements

Before new feature development starts, the following must exist and be accepted:

1. ADR-001 — Data Model Split.
2. ADR-002 — Bounded Contexts.
3. ADR-003 — Transactional Outbox.
4. ADR-004 — AI Candidate Model.
5. ADR-005 — Route Architecture Decision.
6. ADR-006 — Internationalization Fact Model.
7. ADR-007 — Source Attribution and Licensing.
8. ADR-008 — Admin Roles and Publication Authority.
9. Architecture Review Checklist.
10. Target Architecture Blueprint.
11. Architecture Roadmap and Approval Stages.

## Feature readiness rule

Every feature must define:

- bounded context owner;
- source-of-truth chain;
- read/write path;
- event/audit impact;
- migration impact;
- required tests;
- documentation impact.

## Blocked without explicit exception

- adding new AI/publication/quality fields directly to `Place`;
- import or enrichment changing published city/place state;
- AI writing approved/public facts;
- Telegram handlers mutating catalog/publication tables directly;
- destructive admin actions without dry-run/reason/audit;
- new state values without state registry update and tests.

## Allowed during freeze

- bugfixes that preserve existing contracts;
- tests/guards;
- documentation/ADR work;
- diagnostic scripts with dry-run defaults;
- compatibility adapters needed for the architecture migration.

## Exit criteria

Stage 0 is complete when:

- all ADR files exist in repo;
- Confluence has matching architecture pages;
- Jira tasks for Phase 0 exist;
- future work is required to pass the architecture review checklist.

## Next stage

After this gate, proceed to Stage 1 — Data Foundation.
