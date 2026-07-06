# City GO — repository map

Short index for task-scoped context. Read this before broad `grep` or full-repo search.

## Backend

| Path | Responsibility |
|------|----------------|
| `main.py` | App entry |
| `core/` | Config, router setup, auth, taxonomy |
| `routers/` | HTTP API (public + `admin_*`) |
| `services/` | Business logic |
| `models/` | SQLAlchemy models |
| `schemas/` | Pydantic contracts |
| `migrations/` | Alembic revisions |
| `db/` | Session, Base |
| `data/scripts/` | Import workers, OSM scripts |

## Frontend

| Path | Responsibility |
|------|----------------|
| `frontend/src/pages/` | Route pages (public + admin) |
| `frontend/src/pages/admin/` | Admin panel |
| `frontend/src/widgets/` | Route results, shared widgets |
| `frontend/src/shared/debug/` | Debug mode, report send |
| `frontend/src/components/` | PlaceCard, shared UI |

## Tests

| Path | Responsibility |
|------|----------------|
| `tests/` | Backend pytest |
| `frontend/src/**/*.test.tsx` | Frontend vitest |
| `ui-tests/` | Playwright (when used) |

## Docs (load on demand)

| Path | When |
|------|------|
| `docs/cursor/` | Cursor workflow, templates |
| `docs/admin_import_jobs_flow.md` | Import admin contract |
| `docs/debug_reports_and_review_queue_job_links.md` | Debug reports + FK fix |
| `docs/architecture/` | Pipeline architecture |
| `AGENTS.md` | Coding standards (long — read sections only) |

## Critical domains → entry files

| Domain | Start here |
|--------|------------|
| Import / enrichment | `services/import_pipeline/runner.py`, `data/scripts/import_city_osm.py`, `services/review_queue_service.py` |
| Admin import UI | `frontend/src/pages/admin/AdminImportJobsPage.tsx`, `services/admin_city_import_job_payload.py` |
| Destination discovery | `routers/admin_discovery.py`, `services/destination_discovery/` |
| Routes | `services/candidate_retrieval_service.py`, `RouteResultPanel.tsx` |
| Debug reports | `routers/debug_reports.py`, `services/debug_report_service.py`, `frontend/src/shared/debug/` |
| DB / migrations | `migrations/versions/`, `tests/test_alembic_single_head_new.py` |
| CI | `.github/workflows/` |

## Do not index (see `.cursorignore`)

`node_modules`, `.venv`, `frontend/dist`, coverage, artifacts, `data/raw`, logs, local DBs.
