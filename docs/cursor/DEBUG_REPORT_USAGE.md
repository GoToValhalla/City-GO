# Debug report usage in AI sessions

## Reference format (paste in prompt)

```text
Debug report: DBG-A1B2C3D4E5
Admin: /admin/debug-reports/DBG-A1B2C3D4E5
Screen: route | Category: route | Severity: warning
City: zelenogradsk | Request ID: cg_req_abc123
Summary: Route returned 1 point; warnings: LOW_CANDIDATES, SHORT_ROUTE
Failed step: (if import) collecting_places / tourist_core
```

## What to never paste

- `Authorization`, `Cookie`, session tokens.
- Full `sanitized_payload` or `step_details` from chat.
- Precise user GPS (report stores coarse coords by default).
- Telegram message body with secrets.

## Fetching full payload

1. Admin UI: `/admin/debug-reports/{public_id}` → «Полная очищенная диагностика».
2. API: `GET /admin/debug-reports/{public_id}` (admin auth).
3. Give agent **selected fields** only: `warnings`, `reason_codes`, `debug_trace` keys, `backend_context`.

## request_id

Use to correlate with `GET /admin/system-logs?request_id=...` — cite id, do not paste full logs.

## Turning reports into regression tests

1. Extract stable codes: `reason_codes`, warning strings, HTTP status.
2. Minimal fixture from `response_summary` — no production PII.
3. Backend: `tests/test_*_new.py`; frontend: `*.test.tsx`.
4. Assert behavior fix — not snapshot of entire payload.

## Creating reports (manual QA)

- Normal: «Сообщить о проблеме» on route/places screens.
- Debug: `?debug=1` → copy diagnostics or send report.
- Verify: report appears in `/admin/debug-reports`; Telegram only if enabled.
