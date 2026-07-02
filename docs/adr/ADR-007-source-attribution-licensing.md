# ADR-007 — Source Attribution and Licensing Model

Date: 2026-07-02
Status: Accepted
Jira: CITYGO-114

## Context

City GO uses external sources such as OSM and may later combine multiple providers, web extraction, AI enrichment and human edits. Mixing source data without provenance and license boundaries creates legal, operational and data-quality risk.

## Decision

Every raw observation, fact candidate and approved fact must carry source attribution and provenance metadata.

## SourceObservation attribution fields

- provider;
- provider_object_id;
- provider_url if available;
- source_license;
- attribution_text;
- import_run_id;
- import_batch_id;
- raw_payload_checksum;
- observed_at.

## Fact provenance fields

Every `PlaceFactVersion` stores:

- source_type: provider / ai / human / system;
- source_ref;
- confidence;
- created_by;
- created_at;
- validation metadata.

## Rules

- Raw provider payloads remain separated from approved facts.
- Public snapshots must be able to explain source attribution.
- AI-generated values cannot hide source gaps; they reference AiTaskRun and input sources.
- Provider data mixing rules must be explicit per provider/license.
- Deleting or archiving a source does not erase the audit trail unless legally required.

## OSM-specific rule

OSM-derived observations must retain attribution and license metadata. Future proprietary provider data must not be casually merged into raw OSM payload storage without a documented provider-mixing decision.

## Testing and operations

- source attribution required for every SourceObservation;
- public snapshot can expose attribution summary;
- import without provider/license metadata is rejected or quarantined;
- admin can inspect source lineage for any public fact.

## Consequences

Positive:

- legal attribution is traceable;
- source conflicts become explainable;
- public facts can be audited;
- future provider integrations are safer.

Negative:

- more metadata requirements;
- import code must be stricter;
- admin UI must expose lineage.
