---
name: regression-tests
description: Add regression tests for known City GO bugs. Use when encoding a fixed bug or preventing recurrence in routes, catalog, or admin.
---

# Regression tests

## When to use

Known bug, production incident, or “must not happen again” behavior in routes, catalog, import, or admin.

## Inputs

- Bug description or repro steps
- Layer: backend / API / frontend / integration
- Fix included in scope or test-only?

## Steps

1. Find the smallest test file area (`tests/test_*_new.py`, `frontend/**/*.test.tsx`).
2. Write test that fails on old behavior (or documents current bug if fix not in scope).
3. Cover the real failure mode — e.g. service-only in catalog, pharmacy in route, hidden membership visible.
4. Implement fix only if requested; never loosen existing assertions.
5. Run targeted tests only.

## Validation

- Test name/description states the regression scenario
- Would fail if bug reintroduced

## Response format

- **Regression scenario**
- **Test file(s)**
- **Fix included?** (yes/no)
- **Command run + result**
