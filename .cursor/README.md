# City GO — Cursor setup

Short prompts + repo search beat pasted history. Rules and skills live here; `AGENTS.md` is the deep reference — open only when needed.

## Modes

| Mode | Use for |
|------|---------|
| **Ask** | Investigation, reading code, “why does X happen?” |
| **Plan** | Large features, migrations, multi-area changes |
| **Agent** | Scoped implementation with tests |

Start a **new chat** after each logical unit (one endpoint, one admin screen, one CI fix).

## Skills (`.cursor/skills/`)

| Skill | Use when |
|-------|----------|
| `fix-ci` | Red GitHub Actions |
| `backend-endpoint` | New/changed API |
| `admin-ui-change` | Admin frontend |
| `regression-tests` | Lock in a bug fix |
| `deploy-check` | Pre-deploy safety |

Invoke by name in the prompt, e.g. “use fix-ci skill”.

## Token tips

- Ignore/index excludes: `.cursorignore`, `.cursorindexingignore`
- Point to paths: `routers/user_routes.py`, not full file dumps
- **Max Mode** only for broad audits spanning many modules

---

## Prompt templates

### 1. Small fix

```
Task: <one sentence>
Files likely involved: <paths if known>
Constraints: minimal diff, add test if behavior changes
Run: <pytest or npm test target>
```

### 2. Investigation

```
Ask mode. Why does <behavior> happen?
Start from: <router/service/test path>
Return: root cause, relevant files, suggested minimal fix (no code unless asked)
```

### 3. Plan-first feature

```
Plan mode. Feature: <summary>
Areas: backend / frontend / migrations / tests
Requirements: <bullets>
Do not implement yet — output steps, files to touch, risks, test plan
```
