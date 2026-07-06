# Workpack: CI failure

## Goal
<Failing workflow/job — name + link>

## Read first
- `.github/workflows/<workflow>.yml`
- Failing test file from CI log (name only in prompt)
- `docs/cursor/VALIDATION_COMMANDS.md`

## Do not touch
- Unrelated product refactors
- Skipping tests/hooks without user approval

## Likely files
- Test file cited in CI
- Workflow yaml if env/command wrong

## Hard rules
- Fix root cause, not mask
- Distinguish CI env vs local env-only failure

## Tests
```bash
# Reproduce exact CI command from workflow log
.venv/bin/python -m pytest <failing_test> -q --no-cov
```

## Prompt format (context budget)
```text
CI: <workflow> job <name> failed
Step: <step>
Error (last 10 lines summary): ...
Not: full 500-line log
```

## Final response
Root cause · workflow/test fix · local repro · CI expectation
