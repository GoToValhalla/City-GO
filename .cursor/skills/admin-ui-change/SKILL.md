---
name: admin-ui-change
description: Modify City GO admin frontend pages or components. Use for admin panel UI, forms, tables, or API client wiring.
---

# Admin UI change

## When to use

Changes to `frontend/src/pages/admin/` or admin navigation/API usage.

## Inputs

- Screen or route (e.g. `/admin/imports`)
- Expected user action and API endpoint
- Error/loading requirements

## Steps

1. Read existing page + `adminApi.ts` + similar page (e.g. `AdminDataPipelinePage.tsx`).
2. Minimal UI change; Russian labels; no raw technical codes in UI.
3. States: loading, disabled on submit, error banner, success → refresh list.
4. Preserve filters/city selection unless task overrides.
5. Add/update Vitest in `*.test.tsx`.
6. Run: `cd frontend && npm test -- --run <file>` and `npm run build` if types touched.

## Validation

- No infinite loading on API failure
- Write actions blocked while pending

## Response format

- **Screen / behavior**
- **Changed files**
- **Checks run**
- **Risks** (API contract, permissions)
