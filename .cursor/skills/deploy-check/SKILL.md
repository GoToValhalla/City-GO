---
name: deploy-check
description: Prepare or verify deployment safety for City GO. Use before merge/deploy or after large changes.
---

# Deploy check

## When to use

Before production deploy, after migrations, workflow changes, or large feature merge.

## Inputs

- Branch / commit range
- Whether migrations or env vars changed

## Steps

1. `git diff` / changed files — backend, frontend, migrations, `.github/workflows/`.
2. Deployment impact: Alembic head, new env vars (`core/config.py`), feature flags default off?
3. Review CI: required checks, deploy workflow gates, no new secrets in diff.
4. List smoke commands:
   - `GET /health`
   - targeted pytest / frontend build
   - prod: Docker smoke per `scripts/release_smoke.sh` if applicable
5. Go/no-go: blockers vs acceptable follow-up.

## Validation

- Migrations reversible or documented
- Flags default safe for legacy city flow

## Response format

- **Deploy impact** (migrations, config, workflows)
- **Smoke commands**
- **Go / no-go**
- **Risks** for production verification
