# City GO — Controlled Service Extraction Stage 6

Date: 2026-07-02
Status: implementation baseline
Jira: CITYGO-146

## Goal

Stage 6 prevents premature microservice extraction and defines readiness gates for controlled extraction.

## Entities

### ModuleBoundary

Registry of modular monolith boundaries.

Required fields: module code, owner, source-of-truth tables, allowed dependencies, emitted events, consumed events, status.

### ExtractionCandidate

Registry of possible future service extractions.

Required fields: module code, target service name, owner, readiness status, API contract reference, event contract reference, data migration plan, rollback plan.

### IntegrationContract

Contract between modules or services.

Required fields: producer, consumer, protocol, schema reference, version, compatibility policy, status.

### StranglerAdapter

Adapter used during extraction/migration.

Required fields: source module, target service, adapter mode, read/write strategy, fallback strategy, status.

## Rules

- No extraction without owner.
- No extraction without API contract.
- No extraction without event contract.
- No extraction without data migration plan.
- No extraction without rollback plan.
- Strangler adapters must have fallback strategy.

## Tests

Required:

- metadata contains Stage 6 tables;
- test DB creates Stage 6 tables;
- boundary registry contract exists;
- extraction candidate contract exists;
- integration contract exists;
- helper blocks incomplete extraction readiness.
