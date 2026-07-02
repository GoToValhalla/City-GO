# City GO — Publication and Admin Stage 4

Date: 2026-07-02
Status: implementation baseline
Jira: CITYGO-137

## Goal

Stage 4 makes public state changes controlled, auditable and rollbackable.

Publication and admin operations must be event/audit driven. Destructive admin actions require dry run, actor and reason.

## Entities

### PublicationTransitionRule

Defines allowed state transitions.

Required fields: entity type, from state, to state, required role, required quality gate, status.

### QualityGateRule

Defines data quality requirement before publication.

Required fields: gate code, entity type, metric, operator, threshold, severity, status.

### RollbackRequest

Defines rollback intent and audit data.

Required fields: target type, target id, target snapshot version, requested by, reason, status.

### AdminBulkOperation

Defines dry-run/apply operation.

Required fields: operation type, target filter, mode, dry run id, actor, reason, counters, status.

### AdminKillSwitch

Defines operation freeze.

Required fields: switch scope, target, action, actor, reason, status, expires at.

## Rules

- Public state changes are event and audit driven.
- Quality gates must explain blocked publication.
- Rollback requires target snapshot version and reason.
- Bulk apply requires successful dry run.
- High-risk operations can be blocked by kill switch.

## Stage 4 tests

Required:

- metadata contains Stage 4 tables;
- test DB creates Stage 4 tables;
- transition and gate contracts exist;
- rollback helper requires actor, reason and target version;
- bulk helper blocks apply without dry run;
- kill switch helper blocks configured action.

## Exit criteria

Stage 4 is complete when docs, Confluence, Jira, models, helpers and tests exist and CI is green.
