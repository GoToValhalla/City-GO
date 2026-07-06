# Validation commands

Canonical checks by domain. Run narrowest set that covers the change.

## Backend (all Python changes)

```bash
python3 -m compileall routers services schemas models tests -q
```

## Alembic (migrations / new models)

```bash
.venv/bin/python -m pytest tests/test_alembic_single_head_new.py -q --no-cov
```

## Import / review queue

```bash
.venv/bin/python -m pytest tests/test_import_review_queue_job_link_new.py tests/test_review_queue_service.py tests/test_admin_import_status_display_new.py -q --no-cov
```

## Debug reports

```bash
.venv/bin/python -m pytest tests/test_debug_reports_new.py -q --no-cov
```

## Discovery

```bash
.venv/bin/python -m pytest tests/test_destination_discovery_new.py -q --no-cov
```

## Routes

```bash
.venv/bin/python -m pytest tests -q -k "route" --no-cov
```

## Broad backend (when needed)

```bash
.venv/bin/python -m pytest tests -q -k "import or debug_report or review_queue or discovery" --no-cov
```

Note: full `pytest tests` may hit environment-only failures (local Postgres on 127.0.0.1) — report test name and skip if CI-only.

## Frontend

```bash
npm --prefix frontend test -- --run
npm --prefix frontend test -- --run src/path/to/File.test.tsx
npm --prefix frontend run build
```

## Git hygiene

```bash
git status --short
git diff --stat
git diff --check
```

## Cursor config only

```bash
grep -R "alwaysApply: true" .cursor/rules
find docs/cursor -type f | sort
```

No product compile/tests required if only `.cursor/` and `docs/cursor/` changed.
