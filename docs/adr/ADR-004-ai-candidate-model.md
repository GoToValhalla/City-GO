# ADR-004 — AI Candidate Model and Prompt Governance

Date: 2026-07-02
Status: Accepted
Jira: CITYGO-111

## Context

AI enrichment is useful but unsafe if model output directly mutates public catalog fields. LLM output can be wrong, stale, hallucinated, promotional, duplicated or inconsistent with provider facts.

## Decision

AI outputs are candidates. They are never approved facts and never public snapshots by default.

## Target entities

### PromptVersion

- id;
- task_type;
- prompt_hash;
- prompt_text or prompt_reference;
- schema_version;
- status;
- created_at.

### AiTaskRun

- id;
- task_type;
- model_provider;
- model_name;
- prompt_version_id;
- input_hash;
- input_reference;
- output_json;
- tokens_in;
- tokens_out;
- cost_amount;
- latency_ms;
- status;
- error;
- created_at.

### AiCandidate

- id;
- place_id;
- ai_task_run_id;
- field_name;
- locale;
- value_json;
- confidence;
- validation_result_json;
- status: candidate / approved / rejected / superseded;
- created_at.

## Rules

- AI creates `AiTaskRun` and `AiCandidate`.
- Moderation/publication approves or rejects candidates.
- AI cannot write `PlaceSnapshot` directly.
- Prompt/model changes require regression against golden datasets.
- AI cost is tracked by model, prompt version, task type and city.

## Required pipelines

- descriptions;
- address normalization;
- opening hours extraction;
- category classification;
- photo validation/tagging;
- duplicate detection;
- conflict resolution;
- moderation classification;
- quality scoring;
- ranking feature extraction.

## Testing requirements

- prompt regression datasets per task type;
- schema validation for every model output;
- candidate creation tests;
- approval flow tests;
- cost/latency logging tests;
- hallucination/conflict guard tests for critical fields.

## Consequences

Positive:

- AI cannot poison public catalog without approval;
- model changes become auditable;
- costs become measurable;
- prompt regressions can be blocked.

Negative:

- slower pipeline for new AI facts;
- more storage;
- more admin/review tooling needed.
