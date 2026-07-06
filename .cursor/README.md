# City GO — Cursor setup

Short prompts + repo search. Rules auto-apply by path; only `00-city-go-core` is always on.

## Modes

| Mode | Use for |
|------|---------|
| Ask | Investigation |
| Plan | Large multi-area work |
| Agent | Scoped implementation |

New chat per logical unit. Skills: `fix-ci`, `backend-endpoint`, `admin-ui-change`, `regression-tests`, `deploy-check`.

## Rules (`.cursor/rules/`)

| File | Scope |
|------|--------|
| `00-city-go-core.mdc` | Always on |
| `backend-fastapi.mdc` | Python backend |
| `frontend-admin.mdc` | Frontend/admin |
| `tests-quality-gate.mdc` | Tests |
| `ci-deploy.mdc` | CI/workflows |
| `route-engine.mdc` | Route pipeline |
| `data-import.mdc` | Import/taxonomy |

Token excludes: `.cursorignore`, `.cursorindexingignore`.

## Prompt templates

**Small fix:** `Task: … Files: … Run: pytest/npm target`

**Investigate:** `Ask mode. Why …? Start: path. Root cause + minimal fix (no code unless asked).`

**Plan feature:** `Plan mode. Feature: … Areas: … Output steps, files, risks, test plan — no implement.`
