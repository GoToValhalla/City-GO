# ADR-008 — Admin Roles and Publication Authority

Date: 2026-07-02
Status: Accepted
Jira: CITYGO-115

## Context

Publication, rollback, bulk review and destructive admin actions are high-risk operations. Without explicit roles and authority rules, admin tools can accidentally create mass state regressions.

## Decision

Admin authority is role-based and audit-first. Destructive state changes require actor, reason and audit trail.

## Roles

### Viewer

Read-only access to admin dashboards.

### Reviewer

Can approve/reject manual review items and AI candidates within allowed queues.

### Publisher

Can publish approved places/cities and rebuild public snapshots.

### Operator

Can run imports, replay DLQ, trigger dry-run/apply jobs and monitor workers.

### Admin

Can manage roles, feature flags and emergency kill switches.

## Authority rules

- Import/operator role cannot directly publish unless also Publisher.
- AI candidate approval requires Reviewer or higher.
- City publication requires Publisher or higher.
- Rollback requires Publisher/Admin and reason.
- Bulk destructive actions require dry-run first.
- Every destructive action writes audit record.

## Kill switches

Admin must be able to freeze:

- provider import;
- AI task type;
- publication pipeline;
- route generation mode;
- search projection rebuild.

## Audit requirements

Audit every action with:

- actor;
- role;
- action;
- target entity;
- previous state;
- next state;
- reason;
- request id;
- created_at.

## Testing requirements

- role permission tests;
- destructive action requires reason;
- bulk action requires dry-run;
- audit row exists for publication/rollback/hide;
- unauthorized role cannot publish/rollback.

## Consequences

Positive:

- safer admin operations;
- clear operational authority;
- better incident reconstruction.

Negative:

- more auth/role complexity;
- admin actions need more structured forms.
