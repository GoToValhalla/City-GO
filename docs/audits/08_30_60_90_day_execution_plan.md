# 08 — 30/60/90-Day Execution Plan

> Turns audits 01–07 into a practical plan for one main developer. No code changed.
> Task IDs reference File 07 (Top 50) and per-domain backlogs (PL/RE/DP/TG/UX/Slice).

---

## 1. Executive Summary

Three months, one developer, limited resources. Sequence: **30 days = stop the bleeding** (security writes, enforce existing controls, get admin UI working under auth, fix the obvious web/bot UX defects). **60 days = operational maturity** (admin vertical slices, route observability, data-pipeline safety + cron, bot UX cleanup, frontend foundation incl. a map). **90 days = product depth** (route constructor foundation, active-route-session design, recommendations tuning, admin operations maturity).

Guiding rule from the master review: fix the **root causes** (no single source of truth; controls written-but-not-enforced; duplicated systems) rather than chasing leaves. Avoid microservices/K8s/RBAC/rewrites.

---

## 2. 30-Day Plan (Launch Blockers)

Focus: launch blockers, security, migration confidence, place lifecycle, route observability seed, admin shell planning, UI critical fixes.

Tasks (File 07 IDs): 1–12, plus 14, 35, 48.

Outcomes:
- No unauthenticated write endpoints (`/v1/verification/place/*`, `/place-seed/import/` closed).
- `is_route_eligible` enforced; diagnostics match retrieval; dead test fixed.
- Admin UI works under enforced `ADMIN_API_TOKEN` (shell + token).
- Public pages no longer call `/admin/*`.
- Web city context consistent; result grids have loading/empty states.
- Bot exposes its real feature set + location button; false unsupported-city fixed.
- Dead `admin_extra.py` archived; doc drift corrected.

## 3. 60-Day Plan (Operational Maturity)

Focus: admin panel first slices, route stability, data pipeline stability, Telegram UX cleanup, frontend redesign foundation.

Tasks: 13, 15–22, 23–24, 28–34.

Outcomes:
- Admin slices live: Places list, Place detail/edit, Images moderation, Verification queue (audited), Routes, Audit log, Dashboard real metrics.
- Verify paths converged + audited.
- Route per-place drop diagnostics + diagnostics tests + short-route regression fixture.
- Data pipeline: dangerous scripts tested; `enrich_place_images` no longer auto-approves drafts; cron import wired.
- Bot: extend_route button, unified nearby, persistent FSM, city in `/context`.
- Frontend foundation: minimal Leaflet map, server search + pagination.

## 4. 90-Day Plan (Product Depth)

Focus: route constructor foundation, active route session design, route recovery design, recommendations improvement, admin operations maturity.

Tasks: 25–27, 36–47, plus design specs for future features (Route Constructor, Active Route Session, Route Recovery, Smart Detours) and remaining P2.

Outcomes:
- Derived publication helper (single computed visibility) without a data migration.
- OSM importer uses canonical taxonomy + source services; duplicate image path collapsed.
- Route engine: configurable stops/diversity per city density; soft-fail unknown hours; assembly trace timing fixed.
- Mobile bottom nav + city picker; LocationCarousel finished; place-detail map + build-from-here.
- Design docs (not full build) for Route Constructor / Active Route Session / Route Recovery / Smart Detours.

---

## 5. Weekly Milestones

### Week 1 — Security writes + enforcement
- Goals: eliminate unauthenticated writes; enforce eligibility.
- Tasks: 3 (close `/v1/verification/*`), 4 (auth seed import), 1 (enforce `is_route_eligible`), 7 (fix dead test).
- Outputs: 4 endpoints/behaviors fixed + `_new` tests.
- Risks: hidden callers of public verification/seed endpoints → grep callers first; provide token to scripts via env (secrets rule).

### Week 2 — Diagnostics + admin shell
- Goals: trustworthy route diagnostics; admin works under auth.
- Tasks: 2 (diagnostics parity), 5 (admin shell + token), 12 (archive `admin_extra.py`).
- Outputs: parity test; AdminShell/ApiClient/RouteGuard/TokenStorage; PhotoReview under shell.
- Risks: localStorage token acceptable for internal tool; document it.

### Week 3 — Public UX defects
- Goals: remove role confusion; fix city context; add states.
- Tasks: 6 (admin off public page), 8 (city context), 9 (loading/empty states), 26 (hide debug trace), 27 (`/routes` in nav).
- Outputs: Vitest `_new` tests; consistent city across Routes/Nearby/Open-now.
- Risks: regression in existing screens → snapshot critical flows.

### Week 4 — Bot defects + dashboard + searchable
- Goals: bot feature discoverability; honest dashboard; resolve dead field.
- Tasks: 10 (keyboard+location), 11 (unsupported-city), 14 (`audit_events_total`), 35 (`is_searchable` enforce/reserve), 48 (doc drift).
- Outputs: bot tests; dashboard real count; updated `security.md`/`place_visibility.md`.
- Risks: keyboard change affects existing handlers → keep one keyboard source of truth.
- **End of Week 4 = launch-blocker set cleared.**

### Week 5–8 — Admin slices + route obs + data safety + bot + FE foundation
- Goals: operational admin; trustworthy route drops; safe data ops; bot UX; map.
- Tasks: 13, 15–22 (admin slices + verify audit + diagnostics tests), 23–24 (map, search/pagination), 28–34 (bot + data pipeline).
- Outputs: admin vertical slices shipped weekly; per-place drop diagnostics; data-script tests; cron import; Leaflet map.
- Risks: scope creep on admin UI → ship one entity per few days; map kept minimal.

### Week 9–12 — Product depth + remaining debt + future design
- Goals: publication helper; taxonomy/source consolidation; engine tuning; mobile polish; future-feature design docs.
- Tasks: 25, 36–47, design specs for Route Constructor / Active Route Session / Route Recovery / Smart Detours.
- Outputs: derived visibility helper; canonical taxonomy in importer; configurable engine; mobile nav; design docs.
- Risks: avoid premature build of future features — design only; keep migrations out unless trivial.

---

## 6. Definition of Launch Ready

- [ ] No unauthenticated write endpoints anywhere (verification, seed import).
- [ ] Admin UI fully functional under enforced `ADMIN_API_TOKEN`.
- [ ] No `/admin/*` calls from public pages.
- [ ] `is_route_eligible` enforced; diagnostics == retrieval; no dead tests.
- [ ] Every public result grid has loading + empty + error states.
- [ ] Web city context consistent across all screens.
- [ ] Bot's advertised features are all reachable; location sharing available.
- [ ] All admin writes audited (incl. verification path).
- [ ] Single Alembic head invariant holds (already true).
- [ ] P0-4 import-draft behavior intact (already true).
- [ ] `docs/architecture/security.md` matches reality.

(Map and full admin slice set are strongly recommended but can trail launch by weeks if time-boxed.)

---

## 7. What To Stop Doing

- Stop adding publication/visibility booleans — converge toward a derived source of truth.
- Stop maintaining two admin frontends — pick React.
- Stop shipping admin actions on public pages.
- Stop writing tests that describe intended-but-unimplemented behavior (the `_fallback_city_scope` case).
- Stop relying on docs that claim enforced controls that aren't (route eligibility).
- Stop auto-publishing/auto-approving in data scripts where moderation is expected.
- Stop running mass mutations (address backfill `--apply`) automatically on deploy without a gate.

---

## 8. First 10 Implementation Prompts (priority order)

```
PROMPT 1 — Close unauthenticated writes (File 07 #3, #4)
Protect POST /v1/verification/place/{id}/confirm|reject and POST /place-seed/import/ with admin_required
(core/admin_auth.py). Update scripts/production_place_import.py to send Authorization: Bearer from an env var
(secrets rule: request the var name, don't read secret files). Verify callers first. Tests _new: 401 without
token, success with token. Docs: security.md endpoint table. Analyze first; one-block report.
```
```
PROMPT 2 — Enforce route eligibility + diagnostics parity (File 07 #1, #2, #7)
services/candidate_retrieval_service.py must enforce is_route_eligible; route_candidate_diagnostics.py must
count with the same conditions retrieval uses. Rewrite tests/test_candidate_retrieval_city_scope_fallback_new.py
to test the real _fallback_expand_radius. Tests _new: eligibility exclusion, count parity, fallback path.
Docs: place_visibility.md. No scoring/assembly changes. Analyze first; one-block report.
```
```
PROMPT 3 — Admin shell + token auth (File 07 #5, #12)
Create React admin shell (AdminShell/Layout/Sidebar/Topbar/RouteGuard/TokenStorage/ApiClient) that injects
Authorization: Bearer. Migrate PhotoReviewPage under it. Archive routers/admin_extra.py to a legacy folder
(move, not delete). Tests _new: ApiClient attaches Bearer; guard redirects without token. Docs: admin_guide.md.
Do not add a second auth system. Analyze first; one-block report.
```
```
PROMPT 4 — Remove admin from public page + web city context (File 07 #6, #8)
Remove admin moderation buttons from pages/places/PlaceDetailPage.tsx. Introduce a single useCurrentCity()
consumed by RoutesListPage and NearbyPage; remove hardcoded 'zelenogradsk' and Zelenogradsk-center default.
Tests _new (Vitest): no admin buttons on detail; Routes/Nearby use selected city. Frontend only. One-block report.
```
```
PROMPT 5 — Result grid states + meta (File 07 #9, UX-4)
Add shared LoadingSkeleton + EmptyState to NearbyResults, OpenNowResults, PlacesListPage, home PlacesSection.
Fix index.html lang="ru" + real title; localize breadcrumbs. Tests _new: loading→empty transitions. One-block report.
```
```
PROMPT 6 — Bot feature discoverability (File 07 #10, #11)
keyboards/main_menu.py: add request_location button and reconcile keyboard with existing handlers (one source
of truth). Fix false unsupported-city by parsing the city token before the unsupported check. Tests _new.
telegram_bot only; FSM in handlers, logic in services/. One-block report.
```
```
PROMPT 7 — Converge + audit verification paths (File 07 #13, #14)
Add write_admin_audit_log to apply_place_verification; converge POST /admin/places/{id}/verify with
POST /admin/place-verifications/.../verify. Compute audit_events_total in get_admin_dashboard. Tests _new:
verify writes audit; dashboard shows real count. One-block report.
```
```
PROMPT 8 — Admin Places + Images + Audit slices (File 07 #15, #17, #20)
Build Admin Places list (AdminTable + publish/unpublish), Images moderation in shell (+ set-primary),
Audit log viewer (filters). Reuse AdminApiClient. Tests _new. Docs: admin_implementation_status.md. One-block report.
```
```
PROMPT 9 — Route drop diagnostics + tests (File 07 #21, #22)
Add per-place drop diagnostics (id + reason + stage) to route_pipeline_trace; surface radius-fallback-used and
balance-trim counts. Add tests for route_candidate_diagnostics and a short-route regression fixture. No engine
behavior change beyond diagnostics. One-block report.
```
```
PROMPT 10 — Minimal map + server search (File 07 #23, #24)
Add a Leaflet + OSM map layer for nearby results and route result polyline (reuse lat/lng). Wire places search
to /places/search with real pagination/infinite scroll. Tests _new (Vitest). Frontend only. One-block report.
```
