# 02 — Admin Panel Implementation Plan

> Due diligence + phased plan. No code changed. Admin panel is treated as an operational system, not CRUD.
> Classification: REAL DEFECT · TECHNICAL DEBT · PARTIALLY IMPLEMENTED · FUTURE ROADMAP · INTENTIONALLY DEFERRED · REQUIRES VERIFICATION

---

## 1. Executive Summary

The **backend admin API is largely production-ready**: `routers/admin.py` exposes 22 endpoints, all guarded by `Depends(admin_required)` (`core/admin_auth.py`), and most writes emit audit logs via `services/admin_audit_service.py::write_admin_audit_log`. The **frontend is the gap**: there are two disconnected UIs — a standalone `admin/` (vanilla JS + Vite, has a sidebar shell but **no token auth**) and a single React page `frontend/src/pages/admin/PhotoReviewPage.tsx`. Neither sends an `Authorization: Bearer` header, so **all admin UI breaks the moment `ADMIN_API_TOKEN` is enforced** (REAL DEFECT, launch blocker for admin operations).

Key defects: (1) admin UIs lack token auth header; (2) `routers/admin_extra.py` is dead code that duplicates 3 endpoints **without** auth (latent risk if ever registered); (3) two verify paths, one without audit; (4) public unauthenticated verification writes in `routers/verification.py`; (5) `audit_events_total` in dashboard schema is a stub (always 0).

Recommendation: build one React Admin Shell with token auth, then ship vertical slices (Dashboard → Places → Images → Verification → Routes → Audit). Do **not** build JWT/OAuth/RBAC now (single shared token is acceptable for launch).

---

## 2. Backend Admin API Map

Auth model: single shared Bearer token `ADMIN_API_TOKEN` (`core/config.py:50-53`) compared with `hmac.compare_digest` in `core/admin_auth.py::admin_required`, returning a fixed `AdminContext(actor_id="admin-api", actor_role="admin")`. Roles (`ADMIN_ROLES` in `services/admin_extra_service.py`) are declarative only — **not enforced**.

### `routers/admin.py` (prefix `/admin`) — all 22 with `admin_required`

| Method | Path | Function | Service | R/W | Audit | Models | Classification |
|---|---|---|---|---|---|---|---|
| GET | `/admin/dashboard` | `read_admin_dashboard` | `get_admin_dashboard` | R | — | City,Place,PlaceImage,Route | READY FOR UI (note `audit_events_total` stub) |
| GET | `/admin/roles` | `read_admin_roles` | `ADMIN_ROLES` static | R | — | — | READY FOR UI |
| GET | `/admin/cities` | `read_admin_cities` | `get_admin_cities` | R | — | City,Place,PlaceImage | READY FOR UI |
| POST | `/admin/cities/import` | `create_city_import` | `create_city_and_queue_import` | W | ✅ | City | READY FOR UI |
| GET | `/admin/cities/{id}/coverage` | `read_admin_city_coverage` | `admin_coverage` | R | — | City,Place,PlaceImage | READY FOR UI |
| GET | `/admin/import-jobs` | `read_admin_import_jobs` | `get_admin_import_jobs` | R | — | City,Place,PlaceImage | READY FOR UI |
| GET | `/admin/import-jobs/{id}` | `read_admin_import_job` | `get_admin_import_job` | R | — | City,Place,PlaceImage | READY FOR UI |
| GET | `/admin/places` | `read_admin_places` | `get_admin_places` | R | — | Place,City | READY FOR UI |
| POST | `/admin/places` | `create_place_from_admin` | `create_admin_place` | W | ✅ | Place | READY FOR UI |
| PUT | `/admin/places/{id}` | `update_place_from_admin` | `update_admin_place` | W | ✅ | Place | READY FOR UI |
| POST | `/admin/places/{id}/publish` | `publish_place_from_admin` | `publish_place` | W | ✅ | Place | READY FOR UI |
| POST | `/admin/places/{id}/unpublish` | `unpublish_place_from_admin` | `unpublish_place` | W | ✅ | Place | READY FOR UI |
| POST | `/admin/places/{id}/verify` | `verify_place_from_admin` | `verify_place` | W | ✅ | Place | READY FOR UI |
| POST | `/admin/place-images` | `create_place_image_from_admin` | `create_admin_place_image` | W | ✅ | PlaceImage | READY FOR UI |
| GET | `/admin/routes` | `read_admin_routes` | `get_admin_routes` | R | — | Route | READY FOR UI |
| POST | `/admin/routes` | `create_route_from_admin` | `create_admin_route` | W | ✅ | Route | READY FOR UI |
| PUT | `/admin/routes/{id}` | `update_route_from_admin` | `update_admin_route` | W | ✅ | Route | READY FOR UI |
| PUT | `/admin/routes/{id}/points` | `update_route_points_from_admin` | `replace_admin_route_points` | W | ✅ | Route,RoutePlace | READY FOR UI |
| POST | `/admin/routes/{id}/publish` | `publish_route_from_admin` | `publish_route` | W | ✅ | Route | READY FOR UI |
| POST | `/admin/routes/{id}/unpublish` | `unpublish_route_from_admin` | `unpublish_route` | W | ✅ | Route | READY FOR UI |
| GET | `/admin/route-feedback` | `read_admin_route_feedback` | `admin_route_feedback` | R | — | UserSignal | READY FOR UI |
| GET | `/admin/audit-log` | `read_admin_audit_log` | `get_admin_audit_logs` | R | — | AdminAuditLog | READY FOR UI |

### `routers/place_image_review.py` (prefix `/admin/place-images`) — all with `admin_required`

| Method | Path | Function | Service | R/W | Audit | Classification |
|---|---|---|---|---|---|---|
| GET | `/admin/place-images/pending` | `read_pending_place_images` | `get_pending_place_images` | R | — | READY FOR UI |
| POST | `/admin/place-images/{id}/approve` | `post_approve_place_image` | `approve_place_image` | W | ✅ | READY FOR UI |
| POST | `/admin/place-images/{id}/reject` | `post_reject_place_image` | `reject_place_image` | W | ✅ | READY FOR UI |
| POST | `/admin/place-images/{id}/set-primary` | `post_set_primary_place_image` | `set_primary_place_image` | W | ✅ | READY FOR UI |

### `routers/place_verification.py`

| Method | Path | Function | R/W | Auth | Audit | Classification |
|---|---|---|---|---|---|---|
| POST | `/place-verification/enqueue-stale/{city}` | `post_enqueue_stale_places` | W | ✅ | ✅ | READY FOR UI |
| GET | `/place-verification/queue` | `get_pending_verification_tasks` | R | ❌ public | — | REQUIRES VERIFICATION (public read OK?) |
| GET | `/admin/place-verifications/queue` | `get_admin_place_verification_queue` | R | ✅ | — | READY FOR UI |
| POST | `/admin/place-verifications/places/{id}/verify` | `post_admin_verify_place` | W | ✅ | **❌** | NEEDS BACKEND FIX (audit) |
| POST | `/admin/place-verifications/places/{id}/confirm-nearby` | `post_admin_confirm_place_nearby` | W | ✅ | **❌** | NEEDS BACKEND FIX (audit) |
| GET | `/admin/place-verifications/stats` | `get_admin_place_verification_stats` | R | ✅ | — | READY FOR UI |

### `routers/verification.py` (prefix `/v1/verification`) — public

| Method | Path | Function | R/W | Auth | Audit | Classification |
|---|---|---|---|---|---|---|
| GET | `/v1/verification/queue/{city}` | `read_verification_queue` | R | ❌ | — | REQUIRES VERIFICATION |
| GET | `/v1/verification/stats/{city}` | `read_verification_stats` | R | ❌ | — | REQUIRES VERIFICATION |
| POST | `/v1/verification/place/{id}/confirm` | `confirm_place` | W | ❌ | ❌ | UNSAFE / NOT READY |
| POST | `/v1/verification/place/{id}/reject` | `reject_place` | W | ❌ | ❌ | UNSAFE / NOT READY |

### `routers/admin_extra.py` — NOT registered (verified in `core/router_setup.py`)

`/admin/roles`, `/admin/cities/{id}/coverage`, `/admin/route-feedback` — duplicates of `admin.py`, **without `admin_required`**. Classification: **DEAD / UNUSED** (latent UNSAFE if ever wired). Recommend deletion (to Trash per AGENTS.md rule 17).

---

## 3. Frontend Admin Map

| Surface | Path | Shell? | Token auth? | Real vs stub |
|---|---|---|---|---|
| Standalone admin | `admin/` (vanilla JS + Vite, `admin/src/main.js`) | ✅ sidebar (`dashboard,cities,places,photos,routes,audit`) | ❌ **no `Authorization` header** (`main.js:14-24`) | Real API calls for dashboard/cities/import-jobs/places/photos/routes/audit; missing verifications, route-feedback, coverage, PUT edit, route-points, set-primary |
| React photo review | `frontend/src/pages/admin/PhotoReviewPage.tsx` (route `/admin/photo-review`) | ❌ no shell | ❌ no token | Real: pending/approve/reject/set-primary; city hardcoded `zelenogradsk` |
| Public page moderation | `frontend/src/pages/places/PlaceDetailPage.tsx` | ❌ | ❌ | Inline verify/approve buttons on a public page — REAL DEFECT |

**Critical:** All three break under enforced `ADMIN_API_TOKEN` (401). → REAL DEFECT.

---

## 4. Admin Security Model

- Transport: `Authorization: Bearer <ADMIN_API_TOKEN>`; validated server-side (`hmac.compare_digest`).
- Fail-fast: `main.py` lifespan raises if `app_env=="production"` and token missing.
- 401 (no header) / 403 (bad token) / 503 (token not configured).
- Single shared identity (`admin-api`). RBAC not enforced. → INTENTIONALLY DEFERRED (acceptable for launch).
- Gaps: public `/v1/verification/*` writes (REAL DEFECT); frontend has no token store (REAL DEFECT).

Docs to update: `docs/architecture/security.md` does not document the `apply_place_verification` audit gap nor the public verification writes. → TECHNICAL DEBT (doc drift).

---

## 5. Admin Audit Model

`models/admin_audit_log.py` (`admin_audit_logs`): `actor`, `action`, `entity_type`, `entity_id`, `old_value`, `new_value`, `reason`, `created_at`.

Actions emitted: `create_place`, `update_place`, `publish_place`, `unpublish_place`, `verify_place`, `create_city_import_request`, `publish_route`, `unpublish_route`, `create_route`, `update_route`, `replace_route_points`, `create_place_image`, `approve_place_image`, `reject_place_image`, `set_primary_place_image`, `enqueue_stale_verification`.

Missing: `apply_place_verification` / `confirm_place_nearby` (verify path #2) and all `/v1/verification/*`. `audit_events_total` in `AdminDashboardResponse` is never computed (always 0) → PARTIALLY IMPLEMENTED.

---

## 6. Admin Entity Readiness Matrix

| Entity | Backend | Audit | `admin/` UI | React UI | Readiness |
|---|---|---|---|---|---|
| Dashboard | ✅ | n/a | ✅ | ❌ | NEEDS BACKEND FIX (stub metric) + needs React |
| Places | ✅ | ✅ | partial | ❌ | READY FOR UI |
| Place Detail/Edit | ✅ (PUT) | ✅ | ❌ | ❌ | READY FOR UI (no UI yet) |
| Place Images | ✅ | ✅ | partial (no set-primary) | ✅ PhotoReview | READY FOR UI |
| Place Verification | ✅ | **partial (no audit on path #2)** | ❌ | buttons on public page | NEEDS BACKEND FIX |
| Routes | ✅ | ✅ | partial (no edit/points) | ❌ | READY FOR UI |
| Route Feedback | ✅ | n/a (read) | ❌ | ❌ | READY FOR UI |
| Route Debug | ❌ (only X-Debug trace on recommendations) | n/a | ❌ | ❌ | FUTURE ROADMAP |
| Users / User Signals | ❌ no admin endpoint | n/a | ❌ | ❌ | FUTURE ROADMAP |
| Cities | ✅ | ✅ (import) | ✅ | ❌ | READY FOR UI |
| Import Jobs | ✅ | n/a | ✅ | ❌ | READY FOR UI |
| City Coverage | ✅ | n/a | ❌ | ❌ | READY FOR UI |
| Audit Log | ✅ | n/a | ✅ read | ❌ | READY FOR UI |
| Configuration | ❌ | n/a | ❌ | ❌ | FUTURE ROADMAP |
| AI / Recommendations Debug | ❌ | n/a | ❌ | ❌ | FUTURE ROADMAP |

---

## 7. Recommended Admin Architecture

Single React admin (consolidate; retire the vanilla `admin/` or keep only until React parity). Components:

- **AdminShell** — top-level provider (token context, query client).
- **AdminLayout** — sidebar + topbar + content slot.
- **AdminSidebar** — entity nav (Dashboard, Places, Images, Verification, Routes, Cities, Import Jobs, Audit).
- **AdminTopbar** — city selector, actor label, logout (clear token).
- **AdminRouteGuard** — redirect to token entry if no token in `AdminTokenStorage`.
- **AdminTokenStorage** — `localStorage` wrapper (token entered once; sent as `Authorization: Bearer`).
- **AdminApiClient** — fetch wrapper injecting the Bearer header; centralizes 401/403 handling.
- **AdminErrorBoundary** / **AdminLoadingState** / **AdminEmptyState** — consistent states.
- **AdminTable** — sortable/paginated list primitive.
- **AdminDetailPage** — entity detail/edit scaffold.
- **AdminAuditPanel** — reusable audit-log viewer (filter by entity_type/entity_id).

Keep the existing single-token model (no JWT/RBAC).

---

## 8. Vertical Slices Roadmap

For each slice: Goal · Backend · Frontend · Tests · Docs · Risks · DoD · Size · Priority.

**Slice 1 — Admin Shell + Token Auth UI.** Goal: authenticated shell. Backend: none (auth exists). Frontend: AdminShell/Layout/Sidebar/Topbar/RouteGuard/TokenStorage/ApiClient. Tests: ApiClient injects Bearer; guard redirects without token. Docs: `admin_guide.md` token entry. Risks: token in localStorage (acceptable, internal tool). DoD: any existing GET works through shell with token. Size M. **P0.**

**Slice 2 — Dashboard.** Goal: ops overview. Backend: compute `audit_events_total` in `get_admin_dashboard`. Frontend: dashboard cards. Tests: dashboard returns real audit count. Docs: update status. Risks: low. DoD: real metrics shown. Size S. **P1.**

**Slice 3 — Places List.** Backend: ready. Frontend: AdminTable + filters (city, publication_status). Tests: list renders, pagination. DoD: list + publish/unpublish actions. Size M. **P0.**

**Slice 4 — Place Detail/Edit.** Backend: PUT ready. Frontend: AdminDetailPage form + AdminAuditPanel. Tests: edit persists + audit row. DoD: edit + verify + publish from one page. Size M. **P1.**

**Slice 5 — Place Images Moderation.** Backend: ready (+set-primary). Frontend: migrate `PhotoReviewPage` into shell, add set-primary, city selector. Tests: approve/reject/set-primary. DoD: full queue in shell. Size M. **P0.**

**Slice 6 — Place Verification Queue.** Backend: **add audit to `apply_place_verification`**; converge verify paths. Frontend: queue + verify/confirm-nearby + stats. Tests: verify writes audit. DoD: queue actionable + audited. Size M. **P1.**

**Slice 7 — Routes List + Route Detail.** Backend: ready. Frontend: list + detail + publish/unpublish. Tests: list/publish. DoD: route lifecycle from UI. Size M. **P1.**

**Slice 8 — Route Debug Trace.** Backend: expose pipeline trace endpoint (currently only `X-Debug` on recommendations). Frontend: trace viewer. Tests: trace endpoint. DoD: per-route candidate trace visible. Size L. **P2.**

**Slice 9 — Audit Log UI.** Backend: ready. Frontend: AdminAuditPanel full page + filters. Tests: filter by entity. DoD: searchable audit. Size S. **P1.**

**Slice 10 — City Import Jobs / Coverage.** Backend: ready. Frontend: jobs list + coverage charts. Tests: coverage renders. DoD: ops can see import health. Size M. **P2.**

**Slice 11 — Users / User Signals.** Backend: **new read endpoints** (none today). Frontend: list. Tests: endpoint. DoD: read-only signals. Size L. **P3.**

**Slice 12 — Configuration.** Backend: new. **FUTURE ROADMAP.** Size L. **P3.**

**Slice 13 — AI / Recommendations Debug.** Backend: new. **FUTURE ROADMAP.** Size L. **P3.**

---

## 9. What NOT To Do Now

- Do **not** build JWT/OAuth/RBAC (single token is sufficient for launch).
- Do **not** register `admin_extra.py` — delete it.
- Do **not** keep admin moderation buttons on the public `PlaceDetailPage`.
- Do **not** build Users/Config/AI-debug slices before core moderation slices ship.
- Do **not** maintain two admin frontends long-term — consolidate to React.

---

## 10. First Implementation Prompt

```
Implement Admin Slice 1 (Admin Shell + Token Auth UI) and rewire admin frontend calls to send Authorization: Bearer.

Scope:
- Create a React admin shell under frontend/src/pages/admin/ + frontend/src/shared/admin/:
  AdminShell, AdminLayout, AdminSidebar, AdminTopbar, AdminRouteGuard, AdminTokenStorage (localStorage),
  AdminApiClient (fetch wrapper that injects Authorization: Bearer from AdminTokenStorage and handles 401/403).
- Migrate PhotoReviewPage to use AdminApiClient and live under the shell.
- Add a token-entry screen guarded by AdminRouteGuard.

Backend: none (admin_required already exists). Do NOT add a second auth system.

Constraints: do not touch place lifecycle, route engine, telegram. Do not delete the standalone admin/ yet.
Remove admin moderation buttons from the public PlaceDetailPage (move intent to admin shell) — or stub them out.

Tests (suffix _new): AdminApiClient attaches Bearer; RouteGuard redirects without token; PhotoReview approve works through client.
Docs: update docs/admin_guide.md and docs/admin_implementation_status.md.

Analyze first, then implement. Report changed files, tests run, residual risks in one block.
```
