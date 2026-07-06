---
name: fix-ci
description: Investigate and fix failing GitHub Actions or CI checks in City GO. Use when CI is red, workflows fail, or gh run shows errors.
---

# Fix CI

## When to use

CI workflow failed, PR checks red, or user pasted a failing job log.

## Inputs

- Workflow name / job name / run URL or error snippet
- Branch and whether failure is env-specific (Postgres, secrets)

## Steps

1. Read failing log (`gh run view`, Actions UI, or user paste); note first real error, not cascade noise.
2. Locate root cause in workflow (`.github/workflows/`), script, or test — not symptom patches.
3. Minimal fix; do not skip tests, weaken assertions, or disable hooks unless user explicitly asks.
4. Run relevant local checks (targeted pytest, frontend test/build, workflow lint if applicable).
5. If not reproducible locally, document blocker and exact CI command.

## Validation

- Fix addresses root cause
- Targeted tests pass locally or failure reason documented

## Response format

- **Root cause**
- **Changed files**
- **Checks run** (command + result)
- **Risks / what CI still must verify**
