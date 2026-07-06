# Task scopes — file selection matrix

Use one row per session. Do not load the whole repo.

## Import / enrichment bug

| | |
|---|---|
| **Read first** | `services/review_queue_service.py`, `data/scripts/import_city_osm.py`, `services/import_pipeline/runner.py` |
| **Docs** | `docs/admin_import_jobs_flow.md`, `docs/debug_reports_and_review_queue_job_links.md` |
| **Tests** | `tests/test_import_review_queue_job_link_new.py`, `tests/test_admin_import_status_display_new.py`, `-k import` |
| **Rule** | `@50-import-enrichment` |

## Debug report bug

| | |
|---|---|
| **Read first** | `services/debug_report_service.py`, `routers/debug_reports.py`, `frontend/src/shared/debug/` |
| **Docs** | `docs/debug_reports_and_review_queue_job_links.md`, `docs/cursor/DEBUG_REPORT_USAGE.md` |
| **Tests** | `tests/test_debug_reports_new.py`, `AdminDebugReportsPage.test.tsx` |
| **Rule** | `@70-debug-reports` |

## Route bug

| | |
|---|---|
| **Read first** | `services/candidate_retrieval_service.py`, `services/route_builder_v2_service.py`, `RouteResultPanel.tsx` |
| **Docs** | `docs/architecture/` (route sections) |
| **Tests** | `tests/test_*route*`, `RouteResultPanel.test.tsx` |
| **Rule** | `@60-routes` |

## Admin UI bug

| | |
|---|---|
| **Read first** | `frontend/src/pages/admin/<Page>.tsx`, matching `routers/admin_*.py` |
| **Docs** | `docs/admin_import_jobs_flow.md` (if import-related) |
| **Tests** | `frontend/src/pages/admin/*.test.tsx` |
| **Rule** | `@40-admin-ui` |

## Public UI / design

| | |
|---|---|
| **Read first** | `frontend/src/pages/<area>/`, `PlaceCard.tsx`, `frontend/src/shared/debug/` |
| **Docs** | `DESIGN.md` (sections only) |
| **Tests** | `*.test.tsx` for touched components |
| **Rule** | `@30-frontend-react` |

## DB migration

| | |
|---|---|
| **Read first** | `migrations/versions/`, `models/`, `tests/test_alembic_single_head_new.py` |
| **Docs** | `docs/architecture/` |
| **Tests** | `tests/test_alembic_single_head_new.py` |
| **Rule** | `@20-db-migrations` |

## CI failure

| | |
|---|---|
| **Read first** | `.github/workflows/<workflow>.yml`, failing test file from CI log |
| **Docs** | `docs/cursor/VALIDATION_COMMANDS.md` |
| **Tests** | Reproduce failing job command only |
| **Rule** | `@80-testing-ci` |

## Destination discovery

| | |
|---|---|
| **Read first** | `routers/admin_discovery.py`, `services/destination_discovery/`, `AdminDiscoveryPage.tsx` |
| **Docs** | discovery-related docs in `docs/` |
| **Tests** | `tests/test_destination_discovery_new.py`, `AdminDiscoveryPage.test.tsx` |
| **Rule** | `@40-admin-ui`, `@50-import-enrichment` |

## Cursor config

| | |
|---|---|
| **Read first** | `.cursor/rules/`, `docs/cursor/`, `.cursorignore` |
| **Docs** | `docs/cursor/README.md` |
| **Tests** | `grep alwaysApply`, `git diff --check` — no product tests |
| **Rule** | `@90-context-engineering` |
