# 07 — Master Architecture Review

> Connects audits 01–06, identifies root causes, and prioritizes a Top-50 task list. No code changed.
> Classification: REAL DEFECT · TECHNICAL DEBT · PARTIALLY IMPLEMENTED · FUTURE ROADMAP · INTENTIONALLY DEFERRED · REQUIRES VERIFICATION

---

## 1. Executive Summary

City Go is a well-structured FastAPI + SQLAlchemy backend, a React 19 web SPA, an aiogram 3 Telegram bot, a staged route engine, and an OSM/seed data pipeline. The recent stabilization work (admin Bearer auth, single Alembic head, P0-4 import-draft flow) materially improved safety. The codebase follows the project's functional-style, small-file conventions and has broad **service-level** unit tests.

The system's problems are **coherence problems, not rewrite problems**. The same root cause recurs across domains: **multiple overlapping representations of one concept with no single source of truth**, plus **controls that are written but not enforced**. Concretely: 6 publication fields where `is_searchable` is dead and `is_route_eligible` is not enforced in routes; two place-verification paths (one unaudited) plus public unauthenticated verification writes; two admin frontends with no token header; two OSM ingestion branches with two taxonomies; a duplicate legacy `itinerary` route engine.

None of this requires microservices, Kubernetes, or a rewrite. The fixes are surgical: enforce the controls that already exist, close the unauthenticated writes, consolidate duplicated systems, and add the one missing product capability (a map) for launch.

---

## 2. System Map

```
                         ┌──────────────┐
   Telegram (aiogram) ──►│              │
   Web SPA (React)    ──►│  FastAPI app │──► PostgreSQL/PostGIS
   Standalone admin   ──►│  (routers/)  │      (models/, Alembic single head c1f4e7a9d2b3)
                         └──────┬───────┘
                                │ services/
        ┌───────────────────────┼─────────────────────────┐
        ▼                       ▼                         ▼
  Route engine            Place lifecycle            Data pipeline
  (route_builder_flow)    (place_public_visibility)  (import_city_osm / seed import)
        │                       │                         │
        ▼                       ▼                         ▼
  candidate_retrieval     catalog/search/nearby      OSM Overpass / seed JSON
  scoring/assembly        /open-now (aligned)        Nominatim/Geoapify geocoding
  (is_route_eligible      route eligibility          image pipeline (3 tracks)
   NOT enforced)          (NOT enforced)
```

---

## 3. Product Area Map

| Area | Status | Primary files |
|---|---|---|
| Places catalog | OK | `routers/places.py`, `place_service.py`, `place_public_visibility.py` |
| Search | OK (no `is_searchable`) | `routers/place_search.py` |
| Nearby / Open-now | OK (web city-context bug) | `nearby_service.py`, `open_now_service.py` |
| Route generation | Functional; eligibility/diagnostics defects | `route_builder_flow.py` + ~24 services |
| User routes / correction | Functional; `extend_route` bot gap | `user_routes.py` |
| Itinerary (legacy) | Duplicate engine | `routers/itinerary.py` |
| Telegram bot | Functional; keyboard/feature drift | `telegram_bot/*` |
| Admin | Backend ready; frontend broken under auth | `routers/admin.py`, `admin/`, `PhotoReviewPage.tsx` |
| Verification | Two paths; public unauth writes | `verification.py`, `place_verification.py` |
| Image moderation | OK; auto-approve bypass | `place_image_review_service.py`, `enrich_place_images.py` |
| Data pipeline | Draft-safe; unauth seed import; cron not wired | `import_city_osm.py`, `place_seed_import.py` |

---

## 4. Backend Architecture Review

Strengths: clear router→service→model layering; small files; functional style; centralized visibility (`place_public_visibility.py`); centralized admin auth (`core/admin_auth.py`); single Alembic head with invariant test. Weaknesses: write-only fields (`is_searchable`), unenforced control (`is_route_eligible`), duplicated verification logic, dead router (`admin_extra.py`). → Mostly TECHNICAL DEBT, two REAL DEFECTS.

## 5. Frontend Architecture Review

React 19 + Vite 8, raw fetch (no React Query), global CSS, localStorage city. No map, no Telegram WebApp, no bottom nav, inconsistent city context, missing loading/empty states, admin actions on public pages, dead code (`RoutesPage.tsx`, `itinerary.api.ts`). → PARTIALLY IMPLEMENTED for a tourist product.

## 6. Telegram Architecture Review

aiogram 3.15, 11 routers, dual context store, MemoryStorage FSM, good event logging. Keyboard↔handler drift hides features; no location button; `extend_route` no button; silent DB write failures; unauth `/place-discovery/`. → Functional, coherence gaps.

## 7. Admin Architecture Review

Backend production-ready (22 endpoints, auth, mostly audited). Frontend is the blocker: two UIs, neither sends the Bearer token. `admin_extra.py` dead. Two verify paths. → REAL DEFECT (frontend auth), TECHNICAL DEBT (duplication).

## 8. Route Engine Architecture Review

Clean staged pipeline with trace + warnings. Silent cap chain (300→120→scored[:120]→diversity→trim), unenforced `is_route_eligible`, diagnostics/retrieval mismatch, a dead test (`_fallback_city_scope`), duplicate legacy itinerary engine. → Two REAL DEFECTS, rest TECHNICAL DEBT / PARTIALLY IMPLEMENTED.

## 9. Data Architecture Review

Draft-safe imports (P0-4). Two OSM branches + two taxonomies, unauth seed import, cron not wired, dangerous untested scripts, broken `load_seeds.py`. → One REAL DEFECT (unauth import), rest TECHNICAL DEBT.

## 10. Security Architecture Review

Good: admin Bearer auth, hmac compare, fail-fast in prod, audit on most writes, P0-2A enqueue protection. Gaps: public unauth verification writes (`/v1/verification/place/*`), unauth seed import (`/place-seed/import/`), admin frontends without token, `apply_place_verification` no audit, declarative-only roles. → Three REAL DEFECTS (unauth writes + frontend), rest TECHNICAL DEBT.

## 11. Testing Architecture Review

Broad service-level unit tests; Alembic invariant test; P0-4 visibility tests. Gaps: no eligibility/retrieval parity test, dead test targeting non-existent function, no tests for dangerous data scripts, no bot handler/integration tests, no `route_candidate_diagnostics` tests, no `is_searchable` test. → TECHNICAL DEBT.

## 12. Documentation Architecture Review

Rich docs (`docs/architecture/*`, admin guides, place_visibility, migrations, security). Drift: `security.md` omits verification audit gap + public writes; `place_visibility.md` documents `public_route_place_conditions()` as enforced though retrieval doesn't call it; prompt-referenced field names (`source_type`, `import_source`, `data_confidence`) don't exist. → TECHNICAL DEBT (doc drift).

## 13. Infrastructure Review

Docker compose (db, migrate, seed, address-backfill, app), single Alembic head, deploy workflow. Gaps: cron import not wired; auto address backfill `--limit 1000 --apply` on every deploy; dev seed publishes data. → TECHNICAL DEBT / REQUIRES VERIFICATION.

---

## 14. Root Causes

1. **No single source of truth for publication** → 6 fields, dead `is_searchable`, unenforced `is_route_eligible`, `publication_status` not used in filters. Drives lifecycle + route defects.
2. **Controls written but not enforced** → eligibility, searchable, declarative roles. Gives false confidence.
3. **Duplicated systems** → two verify paths, two admin frontends, two OSM taxonomies, duplicate itinerary engine, duplicate image-enrich path.
4. **Frontend lags backend** → backend admin/auth ready, frontend not wired; product missing a map.
5. **Observability/diagnostics drift from reality** → diagnostics counts ≠ retrieval; silent caps; silent DB write failures.
6. **Docs/tests describe intended, not actual** → dead test, doc drift.

Fix the root causes and most leaf issues collapse.

---

## 15. Risks Matrix

| Severity | Items |
|---|---|
| CRITICAL (security/data) | Public unauth verification writes (`/v1/verification/place/*`); unauth seed import (`/place-seed/import/`); admin frontends break under enforced token |
| HIGH (correctness) | `is_route_eligible` not enforced; diagnostics/retrieval mismatch; two verify paths (one unaudited); `apply_place_verification` no audit |
| MEDIUM (debt/quality) | `is_searchable` dead; two OSM taxonomies; duplicate itinerary engine; dangerous untested scripts; image auto-approve on drafts; web city-context bug; missing states |
| LOW (polish) | doc drift; dead code; breadcrumb i18n; `index.html` lang/title; `_city_slug` dup |

---

## 16. What Is Good (do not rewrite)

- Layered router→service→model architecture and small-file functional style.
- Centralized public visibility (`place_public_visibility.py`) — correct and aligned for catalog/search/nearby/open-now.
- Centralized admin auth (`core/admin_auth.py`) with hmac + fail-fast.
- Route pipeline structure + trace + honest warnings.
- P0-4 draft-import safety and its tests.
- Single Alembic head + invariant test.
- Dual context store for the bot.

## 17. What Not To Touch Now

- Do not introduce microservices / Kubernetes / message queues.
- Do not rewrite the Place model or run a big status migration.
- Do not build JWT/OAuth/RBAC.
- Do not rewrite the route engine; fix enforcement + diagnostics.
- Do not touch the legacy itinerary engine yet (decide later).
- Do not delete files outright — move to a legacy folder (AGENTS.md rule 17).

---

## 18. Top 50 Tasks

> Cross-referenced to audit IDs. Size: S/M/L. Dependencies noted.

### P0 — launch blockers (security + correctness)
1. **Enforce `is_route_eligible` in retrieval** (RE-1/PL-1). Files: `candidate_retrieval_service.py`. Dep: none. S. DoD: eligibility-exclusion test passes.
2. **Diagnostics parity with retrieval** (RE-1). Files: `route_candidate_diagnostics.py`. Dep: 1. M. DoD: count parity test.
3. **Close/auth public verification writes** (PL-2). Files: `routers/verification.py`. Dep: none. S. DoD: 401 without token.
4. **Auth the seed import endpoint** (DP-1). Files: `place_seed_import.py`, `production_place_import.py`. Dep: none. S. DoD: 401 without token.
5. **Admin frontend token auth (shell)** (Admin Slice 1). Files: `frontend/src/shared/admin/*`. Dep: none. M. DoD: admin GET works with token.
6. **Remove admin buttons from public PlaceDetailPage** (PL-5/UX-2). Files: `PlaceDetailPage.tsx`. Dep: 5. S.
7. **Fix dead test `_fallback_city_scope`** (RE-2). Files: that test. Dep: none. S.
8. **Fix web city context (Routes/Nearby hardcoded)** (UX-1). Files: `RoutesListPage.tsx`, `NearbyPage.tsx`. Dep: none. S.
9. **Add loading/empty states to result grids** (UX-3). Dep: none. M.
10. **Bot: expose hidden features + request_location** (TG-1). Files: `keyboards/main_menu.py`. Dep: none. M.
11. **Bot: fix false unsupported-city** (TG-2). Dep: none. S.
12. **Delete dead `admin_extra.py`** (move to legacy). Dep: none. S.

### P1 — must-do post-launch (accountability + stability + product)
13. **Audit + converge verify paths** (PL-4/Slice 6). Files: `place_verification_service.py`. Dep: 3. M.
14. **Compute `audit_events_total`** (Slice 2). Files: `admin_service.py`. S.
15. **Admin Places list UI** (Slice 3). M. Dep: 5.
16. **Admin Place detail/edit UI** (Slice 4). M. Dep: 5.
17. **Admin Images moderation in shell** (Slice 5). M. Dep: 5.
18. **Admin Verification queue UI** (Slice 6). M. Dep: 5,13.
19. **Admin Routes list/detail UI** (Slice 7). M. Dep: 5.
20. **Admin Audit log UI** (Slice 9). S. Dep: 5.
21. **Per-place route drop diagnostics** (RE-3). M. Dep: 2.
22. **Tests for diagnostics + short-route regression** (RE-4). M.
23. **Minimal map layer (Leaflet)** (UX-5). L. Dep: none.
24. **Server search + pagination on places** (UX-6). M.
25. **Nearby uses device geolocation** (UX-7). M. Dep: 8.
26. **Hide RouteDebugTrace behind dev flag** (UX-8). S.
27. **Add `/routes` to nav** (UX-9). S.
28. **Bot: extend_route button + handler** (TG-3). S.
29. **Bot: unify nearby rendering** (TG-4). M.
30. **Bot: persistent FSM + surface DB write failures** (TG-5). M.
31. **Bot: show selected city in `/context`** (TG-6). S.
32. **Tests for dangerous data scripts** (DP-2). M.
33. **`enrich_place_images.py` → needs_review (no auto-approve on drafts)** (DP-3/PL-6). M.
34. **Wire `run_due_import_jobs` as scheduled job** (DP-4). M.
35. **Resolve `is_searchable` (enforce or mark reserved)** (PL-3). S.

### P2 — important debt
36. **Derived publication helper (no migration)** (PL-7). M.
37. **Route the direct OSM importer through canonical taxonomy** (DP-5). M.
38. **Use source_observation/presence services in importer** (DP-6). M.
39. **Collapse duplicate image-enrich path** (DP-7). S.
40. **Verify/limit auto address backfill in docker** (DP-9). S.
41. **Assembly trace timing fix** (RE-6). S.
42. **"now" mode: soft-fail unknown hours when pool thin** (RE-7). M.
43. **Configurable num_stops/diversity per city density** (RE-5). M.
44. **Mobile bottom tab bar + city picker** (UX-10). M.
45. **Finish LocationCarousel per DESIGN.md** (UX-11). M.
46. **Place detail map mini + build-from-here prefill** (UX-12). M. Dep: 23.
47. **Bot: rate-limit `/place-discovery/`** (TG-7). M.
48. **Doc drift fixes (security.md, place_visibility.md, field names)** (cross). S.

### P3 — later
49. **Decide fate of legacy itinerary engine** (RE-8). L.
50. **Archive legacy data files + scripts** (DP-8), remove FE dead code (UX-13), unify `category`/`category_id` (PL-9), Users/Config/AI-debug admin slices (Slices 11–13), ratings/reviews + Telegram WebApp (UX-14/15) — all FUTURE ROADMAP / L.

---

### Top 50 grouped (quick index)

- **P0:** 1–12
- **P1:** 13–35
- **P2:** 36–48
- **P3:** 49–50 (+ roadmap bucket)
