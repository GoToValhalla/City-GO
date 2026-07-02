# ADR-006 — Internationalization Fact Model

Date: 2026-07-02
Status: Accepted
Jira: CITYGO-113

## Context

City GO will operate across cities, countries and languages. Names, descriptions, addresses, category labels and AI-generated text cannot be modeled as a single text field without expensive migration later.

## Decision

Localized values are first-class facts. `PlaceFactVersion` includes `locale`, and public snapshots contain locale-aware public fields with deterministic fallback rules.

## Locale model

Use BCP-47 language tags, for example:

- `ru`;
- `en`;
- `kk`;
- `it`;
- `default` for source-native fallback when language is unknown.

## Fact fields affected

- place title;
- short description;
- long description;
- address display text;
- category display label;
- tags;
- route explanations;
- AI summaries.

## Fallback rules

1. Requested locale exact match.
2. City default locale.
3. Source-native value.
4. English fallback if available.
5. Human-readable placeholder only if the field is optional.

Required public fields must not silently fallback to hallucinated AI text.

## Rules

- Every localized fact keeps source, confidence and status.
- AI translations are candidates.
- Human-approved translations become approved fact versions.
- Publication may be per-locale if critical fields are missing.
- Search indexes are built per locale where needed.

## Testing requirements

- fallback order tests;
- publication blocked when required locale facts are missing;
- AI translation remains candidate until approved;
- search projection includes locale-specific fields;
- route text renders deterministic locale fallback.

## Consequences

Positive:

- avoids future i18n rewrite;
- supports multilingual city expansion;
- keeps AI translations auditable.

Negative:

- more fact rows;
- public snapshots become locale-aware;
- admin UI must handle localized review.
