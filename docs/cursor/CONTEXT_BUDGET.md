# Context budget

Keep prompts small. Offload bulk data to artifacts and admin reports.

## Include in prompt

- Task goal and non-goals (3–5 bullets).
- Relevant file paths (5–15, not whole tree).
- Short error summary: step, exception class, one line message.
- Debug report reference: `public_id`, `request_id`, screen, city.
- Test commands to run.
- What was already tried (1–2 lines).

## Do not include

- Full pytest/vitest output (>30 lines) — paste summary + failing test name.
- Full `step_details` / route JSON / import_diff blobs.
- Secrets, tokens, cookies, `.env` values.
- Entire `git diff` — use `git diff --stat` + named files.
- All Confluence/Jira history — link + 2-line summary.

## Tool output offloading

| Instead of | Use |
|------------|-----|
| 500-line CI log | Failing job name + last error block + link |
| Full debug payload | `DBG-XXXXXXXXXX` + admin URL |
| Full route response | point count, warning codes, `request_id` |
| DB row dump | ids, status fields, FK name |

## When to ask for full payload

- Sanitization bug (need before/after redaction sample).
- Schema contract mismatch (need one minimal request/response).
- Ask user to attach **one** redacted JSON file or admin report id — not chat dump.

## Session hygiene

- New chat per task unit.
- `@90-context-engineering` or task template at start.
- Close with: files, tests, risks — not full logs.
