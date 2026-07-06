# Workpack: Debug report bug

## Goal
<Report creation, sanitization, Telegram, or admin list/detail issue>

## Read first
- `docs/cursor/DEBUG_REPORT_USAGE.md`
- `services/debug_report_service.py`
- `routers/debug_reports.py`
- `frontend/src/shared/debug/`

## Do not touch
- Product route/import logic unless report context requires it
- Telegram full JSON delivery

## Likely files
- `schemas/debug_report.py`, `models/debug_report.py`
- `services/admin_alert_service.py`
- `AdminDebugReportsPage.tsx`

## Hard rules
- Full payload in DB/admin only
- Telegram: short summary + link; opt-in
- Redact tokens/cookies/secrets; coarse coords by default

## Tests
```bash
.venv/bin/python -m pytest tests/test_debug_reports_new.py -q --no-cov
npm --prefix frontend test -- --run src/pages/admin/AdminDebugReportsPage.test.tsx
npm --prefix frontend test -- --run src/shared/debug/
```

## Final response
Sanitization behavior · Telegram opt-in · files · tests · env vars (names only)
