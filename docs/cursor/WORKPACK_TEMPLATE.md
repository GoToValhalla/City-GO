# Workpack template

Copy and fill for Agent/Plan sessions.

```markdown
## Task
<type: import | debug_report | route | admin_ui | frontend_ui | db_migration | ci | discovery | cursor_config>

## Goal
<one paragraph>

## Non-goals
- <what not to change>

## Read first
- docs/cursor/REPO_MAP.md
- docs/cursor/TASK_SCOPES.md → <row>
- <2–5 specific files>

## Likely files
- <paths>

## Hard rules
- <from domain rule or ticket>

## Tests
- <exact pytest/vitest commands>

## Final response
1. Root cause
2. Files changed
3. Tests run + results
4. Risks / not verified
5. Commit commands (if asked)
```

## Example (import bug)

```markdown
## Task: import

## Goal
Fix review_queue_items.job_id FK — use city_admin_import_job_id, not ImportBatch.id.

## Read first
- services/review_queue_service.py
- data/scripts/import_city_osm.py
- tests/test_import_review_queue_job_link_new.py

## Tests
.venv/bin/python -m pytest tests/test_import_review_queue_job_link_new.py -q --no-cov
```
