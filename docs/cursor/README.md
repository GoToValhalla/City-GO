# Cursor in City GO

Task-scoped AI sessions: less context, fewer tokens, better outcomes.

## Start here

1. `docs/cursor/REPO_MAP.md` — where code lives; entry points by domain.
2. `docs/cursor/TASK_SCOPES.md` — which files/docs/tests per task type.
3. `docs/cursor/templates/<task>_workpack.md` — copy-paste prompt skeleton.
4. `docs/cursor/CONTEXT_BUDGET.md` — what to include/exclude in prompts.

## Rules

Only **`00-city-go-core.mdc`** is `alwaysApply: true`.  
Domain rules (`10`–`90`) load by **glob** when you edit matching paths, or manually via `@rule-name`.

Do not rely on loading all `docs/` or all tests into context.

## Debug reports in prompts

Reference by id — do not paste full JSON:

```
Report: DBG-ABC123 (/admin/debug-reports/DBG-ABC123)
Request: cg_req_xyz | Screen: route | Summary: 1-point route, LOW_QUALITY
```

See `docs/cursor/DEBUG_REPORT_USAGE.md`.

## Modes

| Mode | Use for |
|------|---------|
| Ask | Investigation, root cause |
| Plan | Multi-area features |
| Agent | Scoped implementation |

New chat per logical unit. Skills: `.cursor/skills/` (fix-ci, backend-endpoint, etc.).

## Validation

`docs/cursor/VALIDATION_COMMANDS.md`
