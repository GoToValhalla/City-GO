# City Go — Cursor Nightly Due Diligence Prompt

Use this file as the full instruction for a long Cursor Agent run.

Run it in Cursor with:

```text
Read docs/prompts/cursor_nightly_due_diligence_prompt.md and execute it exactly.
```

---

# CITY GO — FULL NIGHTLY DUE DILIGENCE

## 1. Role

You are acting as a Principal Software Architect, Staff Backend Engineer, Product Technical Lead, UX reviewer, data quality reviewer, Telegram bot reviewer, route engine reviewer and admin panel reviewer.

Your task tonight is analysis and documentation only.

Do not write runtime code.
Do not change backend code.
Do not change frontend code.
Do not change API contracts.
Do not change migrations.
Do not change tests.
Do not delete or rename existing files.

You may create markdown documents under `docs/audits/`.

Evaluate City Go as a real startup product with one main developer and limited resources. The goal is launch readiness, stability and maintainability, not perfect enterprise architecture.

## 2. Current Project Context

City Go is a travel and city guide product with:

- places catalog
- place details
- nearby places
- open now places
- collections
- route generation
- user routes
- route correction
- route personalization
- recommendations
- AI/query interpretation layer
- Telegram bot
- web app
- admin panel
- place verification
- place image moderation
- data import pipeline
- OSM pipeline
- image enrichment
- future Route Constructor
- future Active Route Session
- future Live Route Editing
- future Route Recovery
- future Smart Detours
- future Business Owner Dashboard
- future Social Layer
- future Gamification

Do not treat roadmap-only future functionality as a current defect.

For every finding, classify it as one of:

1. REAL DEFECT — current functionality is broken, unsafe or incorrect.
2. TECHNICAL DEBT — works now but creates risk or support cost.
3. PARTIALLY IMPLEMENTED — exists but is incomplete or inconsistent.
4. FUTURE ROADMAP — planned feature, not a defect by itself.
5. INTENTIONALLY DEFERRED — acceptable to postpone.
6. REQUIRES VERIFICATION — possible issue, not proven from code.

## 3. Already Completed Stabilization Work

Assume these recent changes exist and verify only when needed:

### 3.1 Cursor Rules

Project rules exist in `.cursor/rules/`. Read and follow them.

### 3.2 Admin Security Slice

Implemented:

- `core/admin_auth.py`
- admin Bearer token auth
- `/admin/*` protection
- place image review admin endpoint protection
- place verification admin endpoint protection
- actor from query/body is no longer trusted
- server-side `AdminContext`
- expanded audit log for image review
- `docs/architecture/security.md`
- `tests/test_admin_auth_new.py`

Do not create a second auth system.
Do not implement full JWT/OAuth/RBAC tonight.

### 3.3 Alembic Migration Invariant

Implemented:

- one active Alembic head: `c1f4e7a9d2b3`
- `docs/architecture/migrations.md`
- `tests/test_alembic_single_head_new.py`

Do not create new merge migrations unless multiple current heads actually exist.

### 3.4 Place Import Draft Flow

Implemented:

- API seed import creates draft places
- OSM import creates draft places
- Admin create place creates draft places
- draft places are hidden from public catalog
- draft places are hidden from route candidates
- `docs/architecture/place_visibility.md`
- `tests/test_place_import_visibility_new.py`

Do not revert this behavior.

### 3.5 load_seeds.py

Previously found:

- not connected to production docker-compose pipeline
- not automatically called
- reads obsolete JSON format
- fails against current ORM format
- legacy/dead code, not active auto-publication risk

Treat it as cleanup unless new evidence proves otherwise.

## 4. Evidence Rules

Every important finding must include:

- file path
- function/class/schema/model/endpoint if possible
- evidence
- impact
- priority
- recommended action

If not proven, write `REQUIRES VERIFICATION`.

Avoid generic recommendations. Be specific.

## 5. Required Output Files

Create directory if missing:

```text
docs/audits/
```

Create and fully populate:

```text
docs/audits/01_place_lifecycle_audit.md
docs/audits/02_admin_panel_implementation_plan.md
docs/audits/03_ui_ux_redesign_audit.md
docs/audits/04_telegram_bot_redesign_audit.md
docs/audits/05_route_engine_deep_audit.md
docs/audits/06_data_pipeline_deep_audit.md
docs/audits/07_master_architecture_review.md
docs/audits/08_30_60_90_day_execution_plan.md
```

Do not paste full file contents in chat. Only summarize at the end.

---

# FILE 1 — `docs/audits/01_place_lifecycle_audit.md`

## Goal

Audit the full lifecycle of `Place`: creation, draft state, publication, catalog visibility, route eligibility, search eligibility, image lifecycle, verification, address enrichment, hiding, deletion/archive behavior and frontend display.

## Must inspect

Models:

- `models/place.py`
- `models/place_image.py`
- `models/place_verification.py`
- `models/place_verification_task.py`
- `models/place_import_event.py`
- `models/place_source_presence.py`
- `models/place_scope_link.py`
- `models/city_import_scope.py`
- `models/admin_audit_log.py`
- `models/route_place.py`
- `models/user_signal.py`

Schemas:

- `schemas/place.py`
- `schemas/admin.py`
- `schemas/place_image.py`
- `schemas/place_verification.py`
- all `schemas/place_seed_*.py`

Services:

- `services/place_service.py`
- `services/place_public_visibility.py`
- `services/place_search_service.py`
- `services/place_filters_service.py`
- `services/place_query_params_service.py`
- `services/place_seed_write_service.py`
- `services/place_seed_import_service.py`
- `services/place_import_lifecycle_service.py`
- `services/place_image_review_service.py`
- `services/place_public_image_service.py`
- `services/place_public_image_attach_service.py`
- `services/place_verification_service.py`
- `services/place_verification_scheduler_service.py`
- `services/admin_service.py`
- `services/admin_extended_service.py`
- `services/candidate_retrieval_service.py`
- `services/source_presence_service.py`
- `services/source_observation_service.py`
- `services/geocoding_service.py`

Scripts:

- `data/scripts/import_city_osm.py`
- `scripts/seed_minimal_data.py`
- `data/scripts/load_seeds.py`
- `data/scripts/backfill_missing_place_addresses.py`
- `data/scripts/cleanup_bad_places.py`
- `data/scripts/cleanup_imported_places_quality.py`
- `data/scripts/review_places.py`

Routers:

- `routers/places.py`
- `routers/place_search.py`
- `routers/nearby.py`
- `routers/open_now.py`
- `routers/admin.py`
- `routers/place_image_review.py`
- `routers/place_verification.py`
- `routers/verification.py`
- `routers/place_seed_import.py`

Frontend:

- `frontend/src/pages/places/PlacesListPage.tsx`
- `frontend/src/pages/places/PlaceDetailPage.tsx`
- `frontend/src/components/places/PlaceCard.tsx`
- `frontend/src/api/places/places.api.ts`
- `frontend/src/entities/place/model/types.ts`
- `frontend/src/shared/place/*`

## Required sections

1. Executive Summary
2. Place Data Model Field Map
3. Place Creation Paths
4. Place State Machine
5. Public Catalog Visibility
6. Route Eligibility
7. Search Eligibility
8. Image Lifecycle
9. Verification Lifecycle
10. Address Lifecycle
11. Delete / Archive / Hide Behavior
12. Frontend Place Display
13. Tests Coverage
14. Lifecycle Risks
15. Recommended Backlog
16. Next Implementation Prompt

For every lifecycle-related field, document:

- purpose
- default
- who writes it
- who reads it
- whether default is safe
- whether field is legacy/current/future
- inconsistency risk

Include at least:

- `status`
- `is_active`
- `is_published`
- `is_visible_in_catalog`
- `is_route_eligible`
- `is_searchable`
- `publication_status`
- `source_type`
- `source_url`
- `import_source`
- `existence_confidence`
- `data_confidence`
- `verification_status`
- `reviewed_at`
- `last_checked_at`
- `address`
- `lat/lng`
- `image_url`
- `place_images`
- `category`
- `category_id`

Explicitly answer:

- Does `is_route_eligible` actually affect route candidate retrieval?
- Can admin disable a place for routes while the route builder still uses it?
- Are public catalog, search and route visibility rules aligned?
- Are image selection rules aligned between backend, scoring and frontend?
- Are address fields reliably shown in UI?

---

# FILE 2 — `docs/audits/02_admin_panel_implementation_plan.md`

## Goal

Prepare a practical phased implementation plan for the City Go admin panel.

Admin panel is an operational tool, not a basic CRUD.

## Must inspect

Backend:

- `routers/admin.py`
- `routers/place_image_review.py`
- `routers/place_verification.py`
- `routers/verification.py`
- `services/admin_service.py`
- `services/admin_extended_service.py`
- `services/admin_audit_service.py`
- `services/place_image_review_service.py`
- `services/place_verification_service.py`
- `schemas/admin.py`
- `schemas/admin_extra.py`
- `models/admin_audit_log.py`
- admin tests

Frontend:

- `frontend/src/pages/admin/*`
- `frontend/src/api/admin/*`
- `frontend/src/App.tsx`
- `frontend/src/shared/api/http.ts`
- `frontend/src/shared/api/endpoints.ts`
- `frontend/src/shared/config/env.ts`
- separate `admin/` folder

Docs:

- `docs/admin_guide.md`
- `docs/admin_city_operations.md`
- `docs/admin_city_update_flow.md`
- `docs/admin_implementation_status.md`
- `docs/architecture/security.md`
- `docs/architecture/place_visibility.md`

## Required sections

1. Executive Summary
2. Backend Admin API Map
3. Frontend Admin Map
4. Admin Security Model
5. Admin Audit Model
6. Admin Entity Readiness Matrix
7. Recommended Admin Architecture
8. Vertical Slices Roadmap
9. What NOT To Do Now
10. First Implementation Prompt

For every admin endpoint include:

- method
- path
- router file
- function
- service
- purpose
- read/write
- auth status
- audit status
- affected models
- existing tests
- missing tests
- frontend readiness
- risk

Classify every endpoint as:

- READY FOR UI
- NEEDS BACKEND FIX
- UNSAFE / NOT READY
- DEAD / UNUSED
- REQUIRES VERIFICATION

For every admin entity include readiness:

- Dashboard
- Places
- Place Detail/Edit
- Place Images
- Place Verification
- Routes
- Route Feedback
- Route Debug
- Users/User Signals
- Cities
- Import Jobs
- City Coverage
- Audit Log
- Configuration
- AI/Recommendations Debug

Recommended architecture must include:

- AdminShell
- AdminLayout
- AdminSidebar
- AdminTopbar
- AdminRouteGuard
- AdminTokenStorage
- AdminApiClient
- AdminErrorBoundary
- AdminLoadingState
- AdminEmptyState
- AdminTable
- AdminDetailPage
- AdminAuditPanel

Create vertical slices:

1. Admin Shell + Token Auth UI
2. Dashboard
3. Places List
4. Place Detail/Edit
5. Place Images Moderation
6. Place Verification Queue
7. Routes List + Route Detail
8. Route Debug Trace
9. Audit Log UI
10. City Import Jobs / Coverage
11. Users / User Signals
12. Configuration
13. AI / Recommendations Debug

For each slice include goal, backend changes, frontend changes, tests, docs, risks, DoD, size and priority.

---

# FILE 3 — `docs/audits/03_ui_ux_redesign_audit.md`

## Goal

Perform a direct UI/UX audit of City Go as a product candidate before launch.

Evaluate as:

- first-time tourist
- returning tourist
- user already in the city
- mobile user
- Telegram user
- competitor user familiar with Google Maps, 2GIS, Tripadvisor and Yandex Maps

Do not implement UI. Do not create mockups. Create a practical redesign plan.

## Must inspect

- `frontend/src/App.tsx`
- `frontend/src/pages/home/*`
- `frontend/src/pages/places/*`
- `frontend/src/pages/routes/*`
- `frontend/src/pages/nearby/*`
- `frontend/src/pages/open-now/*`
- `frontend/src/pages/admin/*`
- `frontend/src/widgets/*`
- `frontend/src/components/*`
- `frontend/src/features/*`
- `frontend/src/entities/*`
- `frontend/src/shared/*`
- `DESIGN.md`
- `docs/architecture/web_bot_ui_redesign.md`
- `docs/architecture/place_route_ui_data_contract.md`

## Required sections

1. Executive Summary
2. Product UX Evaluation
3. Screen-by-Screen Audit
4. Main User Flows
5. Mobile-First Audit
6. Visual Design Audit
7. Information Architecture
8. Competitor Comparison
9. Recommended Redesign Direction
10. UI/UX Backlog
11. First Implementation Prompt

For every major screen include:

1. User goal
2. JTBD
3. Primary action
4. Secondary actions
5. Time to value
6. First-time user experience
7. Returning user experience
8. Mobile experience
9. Navigation cost
10. Cognitive load
11. Missing states
12. Loading states
13. Empty states
14. Error states
15. Accessibility risks
16. Conversion risks
17. Visual/design problems
18. Recommended redesign

Audit these flows:

- first app launch
- build first route
- find a place
- open place details
- find something nearby
- find something open now
- review generated route
- understand route warnings
- start/follow route if supported
- return after previous session

Compare with:

- Google Maps
- 2GIS
- Tripadvisor
- Yandex Maps

Create backlog P0/P1/P2/P3.

---

# FILE 4 — `docs/audits/04_telegram_bot_redesign_audit.md`

## Goal

Audit City Go Telegram Bot as a product channel.

The bot should be a fast, conversational, mobile-first travel assistant, not only a copy of the web UI.

## Must inspect

- `telegram_bot_main.py`
- `telegram_bot/handlers/*`
- `telegram_bot/handlers/place_menu/*`
- `telegram_bot/services/*`
- `telegram_bot/services/context_store/*`
- `telegram_bot/services/text_intent/*`
- `telegram_bot/keyboards/*`
- `telegram_bot/states/*`
- bot-related backend endpoints
- bot-related docs

## Required sections

1. Executive Summary
2. Current Architecture
3. Current Capabilities
4. Telegram User Flows
5. Telegram UX Audit
6. Telegram-Specific Opportunities
7. What Should NOT Be In Telegram
8. Security and Identity
9. Recommended Bot Architecture
10. Telegram Bot Backlog
11. First Implementation Prompt

Build scenario maps for:

1. new user opens bot
2. user selects city
3. user shares location
4. user enters address manually
5. user requests route
6. user corrects route
7. user asks for nearby places
8. user searches place by text
9. user returns later
10. user changes preferences
11. user is already walking
12. user deviates from route if future/roadmap exists

For each scenario include:

- current messages
- buttons
- number of steps
- friction
- drop-off risk
- missing recovery
- recommended flow

Audit security:

- Telegram user id handling
- initData verification
- context storage
- write actions
- user signals
- privacy risks
- abuse risks

Create backlog P0/P1/P2/P3.

---

# FILE 5 — `docs/audits/05_route_engine_deep_audit.md`

## Goal

Perform the deepest audit of the Route Engine.

Explain why routes may be too short, unstable, non-diagnostic or inconsistent.

## Must inspect

Entry points:

- `routers/recommendations.py`
- `routers/user_routes.py`
- `routers/itinerary.py`
- route-related frontend clients
- telegram route clients

Core pipeline:

- `services/route_builder_service.py`
- `services/route_builder_flow.py`
- `services/context_merge_service.py`
- `schemas/merged_context.py`
- `services/candidate_retrieval_service.py`
- `services/route_candidate_diagnostics.py`
- `services/place_validation_service.py`
- `services/place_runtime_defaults.py`
- `services/hard_filters_service.py`
- `services/route_filter_policy.py`
- `services/route_filter_reasons.py`
- `services/scoring_service.py`
- `services/route_assembly_service.py`
- `services/route_assembly_optimizer.py`
- `services/route_diversity_policy.py`
- `services/route_time_ordering_service.py`
- `services/time_aware_service.py`
- `services/route_budget_fit_service.py`
- `services/route_finalize_service.py`
- `services/route_quality_warnings.py`
- `services/route_pipeline_warnings.py`
- `services/route_pipeline_trace.py`

Related:

- user routes
- correction engine
- replan service
- itinerary legacy pipeline
- route feedback
- route analytics
- Telegram route flow
- frontend route flow

## Required sections

1. Executive Summary
2. Entry Point Map
3. Full Pipeline Map
4. Candidate Loss Map
5. Scoring Review
6. Filtering Review
7. Assembly Review
8. Correction / Replan Review
9. Observability / Warnings Review
10. Future Route Features Gap Analysis
11. Route Engine Risks
12. Route Engine Stabilization Backlog
13. First Implementation Prompt

For every pipeline stage include:

- input
- output
- files
- services
- models
- schemas
- candidate count changes
- fallback
- silent fallback
- hardcoded caps
- warnings
- trace fields
- tests
- risks

Check specifically:

- `scored[:50]`
- diversity caps
- budget trim
- synthetic hours
- route eligibility
- expected stops
- warnings
- silent drops
- mismatch between diagnostics and actual retrieval

Create backlog P0/P1/P2/P3.

---

# FILE 6 — `docs/audits/06_data_pipeline_deep_audit.md`

## Goal

Audit ingestion, enrichment, validation, cleanup and publication flows.

## Must inspect

- `data/scripts/*`
- `scripts/*import*`
- `scripts/production_place_import.py`
- `scripts/seed_minimal_data.py`
- `data/seeds/*`
- `data/raw/*`
- `data/enrichment/*`
- `services/place_seed_*`
- `services/import_*`
- `services/place_import_*`
- `services/source_*`
- `services/geocoding_service.py`
- image enrichment pipeline
- docs related to data refresh/import

## Required sections

1. Executive Summary
2. Data Sources Map
3. Import Scripts Map
4. Seed Data Map
5. OSM Pipeline Review
6. Address Pipeline Review
7. Image Pipeline Review
8. Taxonomy Review
9. Data Quality Risks
10. Data Pipeline Backlog
11. First Implementation Prompt

For every script include:

- purpose
- inputs
- outputs
- production-used or not
- idempotency
- failure behavior
- publication behavior
- tests
- risks

For seed/raw/enrichment files include:

- current or legacy
- format
- model compatibility
- source of truth or artifact
- keep/archive recommendation

Create backlog P0/P1/P2/P3.

---

# FILE 7 — `docs/audits/07_master_architecture_review.md`

## Goal

Create a complete architecture review connecting all audits and identifying root causes.

## Must inspect

- backend
- frontend
- Telegram
- route engine
- data pipeline
- admin
- security
- tests
- docs
- infrastructure
- current backlog

## Required sections

1. Executive Summary
2. System Map
3. Product Area Map
4. Backend Architecture Review
5. Frontend Architecture Review
6. Telegram Architecture Review
7. Admin Architecture Review
8. Route Engine Architecture Review
9. Data Architecture Review
10. Security Architecture Review
11. Testing Architecture Review
12. Documentation Architecture Review
13. Infrastructure Review
14. Root Causes
15. Risks Matrix
16. What Is Good
17. What Not To Touch Now
18. Top 50 Tasks

Top 50 tasks must be grouped by:

- P0
- P1
- P2
- P3

For each task:

- title
- why
- files
- dependency
- size
- DoD

---

# FILE 8 — `docs/audits/08_30_60_90_day_execution_plan.md`

## Goal

Turn all audits into a practical execution plan for one main developer.

## Required sections

1. Executive Summary
2. 30-Day Plan
3. 60-Day Plan
4. 90-Day Plan
5. Weekly Milestones
6. Definition of Launch Ready
7. What To Stop Doing
8. First 10 Implementation Prompts

30-day focus:

- launch blockers
- security
- migration confidence
- place lifecycle
- route observability
- admin shell planning
- UI critical fixes

60-day focus:

- admin panel first slices
- route stability
- data pipeline stability
- Telegram UX cleanup
- frontend redesign foundation

90-day focus:

- route constructor foundation
- active route session design
- route recovery design
- recommendations improvement
- admin operations maturity

Break into:

- Week 1
- Week 2
- Week 3
- Week 4
- Week 5-8
- Week 9-12

For every week:

- goals
- tasks
- outputs
- risks

Write 10 ready-to-copy implementation prompts, ordered by priority.

---

# Final Chat Report

After creating all files, reply in one text block only.

Do not paste full file contents.

Report:

1. Confirm all 8 files were created.
2. List exact paths.
3. Main conclusion from each file.
4. Top 10 tasks across the whole project.
5. Which file should be reviewed first tomorrow.
6. Which implementation task should be started first.
7. Mention if any file could not be created.

This is a due diligence task, not a coding task.

Produce documents useful for real implementation work tomorrow.
