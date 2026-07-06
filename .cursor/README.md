# City GO — Cursor setup

**Start:** `docs/cursor/README.md` → `REPO_MAP.md` → `TASK_SCOPES.md` → task template.

## Context efficiency

- Only **`00-city-go-core.mdc`** is always on (`alwaysApply: true`).
- Domain rules `10`–`90` load by **glob** on matching paths or via `@rule`.
- Do **not** paste large logs — use debug report ids / `docs/cursor/CONTEXT_BUDGET.md`.
- Ignore/index excludes: `.cursorignore`, `.cursorindexingignore` (venv, dist, artifacts, raw data).

## Rules (`.cursor/rules/`)

| File | Scope |
|------|--------|
| `00-city-go-core.mdc` | Always on — invariants only |
| `10-backend-fastapi.mdc` | Routers, services, schemas |
| `20-db-migrations.mdc` | Models, migrations, Alembic |
| `30-frontend-react.mdc` | Public frontend + debug mode |
| `40-admin-ui.mdc` | Admin panel |
| `50-import-enrichment.mdc` | Import, review queue, discovery |
| `60-routes.mdc` | Route engine |
| `70-debug-reports.mdc` | Debug reports + Telegram |
| `80-testing-ci.mdc` | Tests, CI workflows |
| `90-context-engineering.mdc` | Manual — token budget |

Legacy rules archived: `.trash/cursor-rules-legacy/`

## Workpack templates

`docs/cursor/templates/` — import, debug report, route, frontend UI, migration, CI, design.

## Skills

`.cursor/skills/` — `fix-ci`, `backend-endpoint`, `admin-ui-change`, `regression-tests`, `deploy-check`.

## Modes

| Mode | Use for |
|------|---------|
| Ask | Investigation |
| Plan | Large multi-area work |
| Agent | Scoped implementation |

New chat per logical unit.

## Quick prompt

```text
Task: <goal>
Read first: docs/cursor/TASK_SCOPES.md → <row>
Template: docs/cursor/templates/<name>_workpack.md
Tests: docs/cursor/VALIDATION_COMMANDS.md
```
