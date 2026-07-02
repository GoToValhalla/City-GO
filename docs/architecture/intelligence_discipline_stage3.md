# City GO — Intelligence Discipline Stage 3

Date: 2026-07-02
Status: implementation baseline
Jira: CITYGO-131

## Goal

Stage 3 makes enrichment prompts versioned, testable and budget-controlled.

Model output is candidate data by default. Approved facts and public snapshots are created only through review and publication flow.

## Entities

### PromptVersion

Stores prompt identity and rollout metadata.

Required fields: task type, version, prompt hash, prompt reference, output schema version, status, rollout policy, owner, changelog.

### GoldenDataset

Versioned evaluation dataset for a task type.

Required fields: task type, dataset version, locale, city scope, minimum pass rate, status.

### EvaluationCase

One evaluation case.

Required fields: dataset id, case key, input payload, expected output, expected decision, severity, tags.

### RegressionGateRun

One prompt/model evaluation run against a dataset.

Required fields: prompt version, dataset, model provider/name, pass status, pass rate, failed cases count, score payload, failure summary.

### CostBudgetPolicy

Budget policy by task/model/city.

Required fields: task type, model provider/name, city id, period, max tokens, max cost, action when exceeded, status.

## Rules

- output is candidate data by default;
- prompt/model changes require regression gate before active rollout;
- candidate approval goes through review and publication flow;
- cost is tracked by task, model and city;
- validation must detect conflict risk before approval.

## Stage 3 tests

Required:

- metadata contains Stage 3 tables;
- test DB creates Stage 3 tables;
- PromptVersion has version/hash/schema/status fields;
- GoldenDataset and EvaluationCase contain threshold/input/expected fields;
- RegressionGateRun stores scores and pass status;
- CostBudgetPolicy stores token/cost/action fields;
- helper blocks promotion when gate fails;
- helper blocks run when cost budget is exceeded.

## Exit criteria

Stage 3 is complete when docs, Jira, models, helpers and tests exist and CI is green.
