# Workpack: DB migration

## Goal
<New table/column/FK; fix Alembic head>

## Read first
- `migrations/versions/` (latest head)
- `models/` + `models/__init__.py`
- `tests/test_alembic_single_head_new.py`

## Do not touch
- Weakening FK to hide application bugs
- Unrelated product logic

## Likely files
- `migrations/versions/<new_revision>.py`
- `db/base.py`

## Hard rules
- Single Alembic head
- Update head revision + count in `test_alembic_single_head_new.py`
- SQLite-compatible patterns for test DB

## Tests
```bash
.venv/bin/python -m pytest tests/test_alembic_single_head_new.py -q --no-cov
```

## Final response
Revision id · tables added · head count · migration risks · deploy upgrade note
