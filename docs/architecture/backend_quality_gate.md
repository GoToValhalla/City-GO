# Backend Quality Gate

`scripts/backend_quality_gate.py` is the custom backend linter required by the
project coding rules.

## What It Checks

- Python source files in backend/script folders are at most 100 lines.
- Direct Python files per module folder stay within 2..10 files.
- Functions have cyclomatic complexity at most 5.
- `pytest.ini` has a coverage fail-under floor of 100%.

## Baseline Policy

The current repository contains legacy debt that predates this gate. Those known
violations are listed in `scripts/backend_quality_baseline.txt`.

The baseline is intentionally explicit:

- new files and modules are checked strictly;
- existing entries should be removed after refactors;
- adding a new baseline entry requires a documented reason in change history or
  the task notes.

## Release Flow

`scripts/release_checks.sh` runs the backend quality gate before tests,
migrations, smoke checks and data coverage checks.

Manual run:

```bash
.venv/bin/python scripts/backend_quality_gate.py
```

## Current QA Stabilization Notes

Backend regression runs use the CI-style environment with SQLite and `--no-cov`
for fast P0 feedback. The coverage run is still supported by `pytest.ini`; on
22.06.2026 the full backend suite passed at 81.51% total coverage with the 75%
floor.

Route stabilization tests now cover the key non-zero route invariants around
city-wide retrieval fallback, GPS-to-city-center fallback, interest/exclusion
normalization, emergency assembly recovery, time-aware behavior and budget fit.
