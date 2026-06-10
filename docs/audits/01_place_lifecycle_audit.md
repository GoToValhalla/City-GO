# 01 — Place Lifecycle Audit

> Due diligence, analysis only. No code changed. Every finding references concrete files/functions/models.
> Classification legend: REAL DEFECT · TECHNICAL DEBT · PARTIALLY IMPLEMENTED · FUTURE ROADMAP · INTENTIONALLY DEFERRED · REQUIRES VERIFICATION

---

## 1. Executive Summary

The `Place` lifecycle is functional and, after P0-4, safe by default for imports (new imported places are `draft`). However the lifecycle is governed by **6 overlapping visibility/publication fields** with **no single source of truth**, and two of them are effectively **write-only dead fields** in the read path:

- **`is_searchable`** — written by admin publish/unpublish, import, seed (`services/admin_service.py:114,142`, `services/place_seed_write_service.py:14`, `data/scripts/import_city_osm.py:504`) but **never read as a filter** in any service/router. → REAL DEFECT (dead field gives false sense of control).
- **`is_route_eligible`** — enforced only in `public_route_place_conditions()` (`services/place_public_visibility.py:36`), which **the route engine does not call**. Route retrieval uses `public_place_conditions()` (without route eligibility). → REAL DEFECT (admin cannot actually disable a place for routes).

Catalog, search, nearby and open-now visibility ARE aligned (all funnel through `public_place_conditions()`). Route eligibility is the one misaligned surface.

Top lifecycle risks: (1) `is_route_eligible` not enforced; (2) `is_searchable` dead; (3) two parallel verification mechanisms with inconsistent audit; (4) image auto-approve path can attach images to draft places; (5) public unauthenticated verification write endpoints.

---

## 2. Place Data Model Field Map

Source: `models/place.py`, `schemas/place.py`, `schemas/admin.py`.

| Field | Purpose | Default (model) | Who writes | Who reads | Default safe? | Legacy/Current/Future | Inconsistency risk |
|---|---|---|---|---|---|---|---|
| `status` | Operational status (`active`/`draft`/`closed`/`hidden`) | `"active"` (`place.py:26`) | OSM import, seed, cleanup, admin | `public_place_conditions()` (`place_public_visibility.py:25`), hard filters | Yes | Current | Overlaps with `is_active`; both gate visibility |
| `is_active` | Physically active (not closed/removed) | `True` (`place.py:59`) | import, cleanup (`cleanup_bad_places.py`), seed | `public_place_conditions()` | Yes | Current | Overlaps with `status` |
| `is_published` | Passed moderation, allowed public | `True` (`place.py:40`) | admin publish/unpublish, import (draft=False) | `public_place_conditions()` | **Risky default** (True) mitigated by import overrides (P0-4) | Current | Default True is legacy-compat only |
| `is_visible_in_catalog` | Shown in catalog | `True` (`place.py:41`) | admin, import | `public_place_conditions()` | Risky default, mitigated | Current | Redundant with `is_published` in practice |
| `is_route_eligible` | Eligible for routes | `True` (`place.py:42`) | admin, import | **Only `public_route_place_conditions()` + diagnostics** — NOT retrieval | **NOT ENFORCED in routes** | Current (broken) | REAL DEFECT |
| `is_searchable` | Indexed in search | `True` (`place.py:43`) | admin, import, seed | **Nobody (write-only)** | N/A | Current (dead read) | REAL DEFECT |
| `publication_status` | `draft`/`published`/`unpublished` | `"published"` (`place.py:44`) | admin, import | Documented as source of truth; **not used in any SQL filter** | Risky default, mitigated | Current | Not enforced; the 3 booleans are what actually filter |
| `publication_comment` / `published_at` / `unpublished_at` | Audit metadata | NULL | admin publish/unpublish (`admin_service.py`) | admin UI only | Yes | Current | — |
| `source` / `source_url` | Provenance (`osm`, `tourist_page`) | NULL | OSM/seed import | dedup (`_find_existing_place`), route scope | Yes | Current | Naming: prompt mentions `source_type`/`import_source` which do NOT exist; actual field is `source` |
| `confidence` | Import confidence 0–1 | NULL | OSM import (0.7), seed | scoring inputs | Yes | Current | Distinct from `existence_confidence_score` |
| `existence_confidence_score` / `existence_confidence_level` | Existence certainty | `0` / `"unknown"` (`place.py:28-29`) | `backfill_place_confidence.py`, verification | verification logic | Yes | Current | Two confidence systems coexist |
| `verification_status` | `unverified`/verified/... | `"unverified"` (`place.py:30`) | verification services | verification queue, scoring | Yes | Current | Two verify paths write it differently |
| `verification_source/method/verified_at/verified_by` | Verification metadata | NULL | verification services | admin UI | Yes | Current | — |
| `needs_recheck_at` | Re-verification schedule | NULL | scheduler (`place_verification_scheduler_service.py`) | enqueue-stale | Yes | Current | — |
| `verification_comment` | Note | NULL | verification | admin | Yes | Current | — |
| `address` | Display address | NULL | OSM tags, Nominatim backfill | UI, `PlaceCard` | Yes | Current | Often empty for OSM places → backfill needed |
| `lat` / `lng` | Coordinates | NOT NULL (required) | import, seed | distance calc (`candidate_retrieval_service.py`), nearby | Yes | Current | Hard filter `no_coordinates` if 0/null |
| `image_url` | Primary image (denormalized) | NULL | `enrich_place_images.py`, image review set-primary | `PlaceCard`, scoring | Yes | Current | Denormalized; can drift from `place_images` |
| `category` (string) | Free category code | NULL | import, seed | hidden-category filter, diversity, scoring | Yes | Current | Coexists with `category_id` FK |
| `category_id` (FK) | Category reference | NULL | import, seed | joins, admin | Yes | Current | Dual category system (string + FK) |
| `average_visit_duration_minutes` | Time budget input | NULL | import, runtime defaults | route assembly | Yes | Current | Runtime default clamps if NULL |
| `opening_hours` (JSONB) | Hours | NULL | import, seed | open-now, time-aware filters | Yes | Current | Synthetic hours injected at runtime if missing |

> Fields named in the prompt that do **NOT** exist in the model: `source_type`, `import_source`, `data_confidence`, `reviewed_at` (the latter exists on `PlaceImage`, not `Place`), `last_checked_at` (exists on `PlaceImage:57`, not `Place`). The closest `Place` equivalents are `source`, `confidence`/`existence_confidence_score`, `verified_at`/`needs_recheck_at`. → REQUIRES VERIFICATION on doc/spec naming drift.

`PlaceImage` lifecycle fields (`models/place_image.py`): `status` (`needs_review`→`approved`/`rejected`/`active`/`unavailable`), `is_primary`, `reviewed_by`, `reviewed_at`, `last_checked_at`. `PUBLIC_PLACE_IMAGE_STATUSES = {approved, active}` (`place_image.py:14`).

`PlaceVerification` (`models/place_verification.py`): append-only audit log of confidence transitions (`status`, `confidence_score_before/after`, `verifier`, geo distance, photo).

---

## 3. Place Creation Paths

| Path | File / Function | Publication state created | Classification |
|---|---|---|---|
| Admin create | `services/admin_service.py::create_admin_place` (schema `AdminPlaceCreate`, `schemas/admin.py:20-25`) | draft (`is_published=False`, `publication_status="draft"`) | OK |
| API seed import | `services/place_seed_write_service.py::write_place_seed_item` (+ `_IMPORT_DRAFT_DEFAULTS:8-16`) | draft (new) / unchanged (existing) | OK (P0-4) |
| OSM direct import | `data/scripts/import_city_osm.py::_apply_import` (`:499-505`) | draft | OK (P0-4) |
| Dev seed | `scripts/seed_minimal_data.py::get_or_create_place` (`:273-278`) | published (explicit) | INTENTIONALLY DEFERRED (dev only) |
| Legacy JSON seed | `data/scripts/load_seeds.py::load_places` (`Place(**item)`) | would be published (model default) — but **crashes** on current schema (`name`/`active` invalid kwargs) | TECHNICAL DEBT (dead code, confirmed crash) |
| Generic create | `services/place_service.py::create_place` (schema default `is_published=True`) | published | REQUIRES VERIFICATION (who calls it? not in admin flow) |

---

## 4. Place State Machine

```
                    ┌───────────────────────────────────────┐
   import/seed ───► │ DRAFT                                  │
                    │ is_published=F, is_visible=F,          │
                    │ is_route_eligible=F, publication=draft │
                    └───────────────┬───────────────────────┘
                                    │ POST /admin/places/{id}/publish
                                    ▼
                    ┌───────────────────────────────────────┐
                    │ PUBLISHED                              │ ──unpublish──► UNPUBLISHED
                    │ all flags True, publication=published  │ ◄──publish───
                    └───────────────────────────────────────┘
   operational status (status / is_active) is a SEPARATE axis:
   active ──cleanup/missing-source──► hidden (is_active=False, status="hidden"/"removed_from_source")
```

Two orthogonal axes — **publication** (admin) and **operational** (`status`/`is_active`, import/cleanup) — are not unified. → TECHNICAL DEBT.

---

## 5. Public Catalog Visibility

`GET /places` → `services/place_service.py::get_places` → `apply_place_filters` (`place_filters_service.py`) → `apply_public_place_visibility` → `public_place_conditions()`:

```22:33:services/place_public_visibility.py
def public_place_conditions() -> tuple[Any, ...]:
    return (
        _true_or_null(Place.is_active),
        or_(Place.status.is_(None), Place.status == PUBLIC_ACTIVE_STATUS),
        _true_or_null(Place.is_published),
        _true_or_null(Place.is_visible_in_catalog),
        or_(Place.category.is_(None), Place.category.notin_(tuple(PUBLIC_HIDDEN_CATEGORIES))),
    )
```

Draft places excluded ✓ (verified by `tests/test_place_import_visibility_new.py`). `_true_or_null` allows NULL for legacy compat. — OK.

---

## 6. Route Eligibility

**Does `is_route_eligible` actually affect route candidate retrieval? → NO. REAL DEFECT.**

`services/candidate_retrieval_service.py::_query_places` uses `public_place_conditions()` (no route eligibility) plus a **scope** filter `_scope_is_route_visible()`:

```41:48:services/candidate_retrieval_service.py
        query = select(Place).where(
            distance_expr <= ctx.radius_meters,
            *public_place_conditions(),
        )
        query = query.join(City).where(City.is_active.is_(True), City.launch_status == "published")
```

`is_route_eligible` only appears in `public_route_place_conditions()` (`place_public_visibility.py:36`) and in diagnostics counts (`route_candidate_diagnostics.py:24-27`). Retrieval never calls it.

**Consequence:** an admin who sets `is_route_eligible=False` on a published place will NOT remove it from generated routes. The diagnostics panel will report a different "route visible" count than what retrieval actually uses. → REAL DEFECT + diagnostics mismatch.

**Can admin disable a place for routes while the builder still uses it? → YES (the defect).**

---

## 7. Search Eligibility

`GET /places/search` → `routers/place_search.py::search_places` → `get_places` → same `apply_place_filters` → `public_place_conditions()`. Text match via `place_search_service.py::apply_place_text_search` (title/slug only).

**`is_searchable` is never referenced in search.** Search visibility == catalog visibility. → `is_searchable` is a REAL DEFECT (dead field) — it implies a control that does not exist.

---

## 8. Image Lifecycle

```
candidate (enrich_place_images.py / image pipeline)
   → PlaceImage(status=needs_review)        [manual queue]
   → admin GET /admin/place-images/pending
   → approve  → status=approved, is_primary, place.image_url synced, audit ✓
   → reject   → status=rejected, audit ✓
   → set-primary → audit ✓
```

- Review service: `services/place_image_review_service.py` (audit logging present for approve/reject/set-primary).
- Public read uses `PUBLIC_PLACE_IMAGE_STATUSES={approved,active}` and `attach_public_images` (`place_public_image_attach_service.py`).
- **Risk:** `data/scripts/enrich_place_images.py --apply` **auto-approves** images (`status=approved`, `is_primary=True`) and syncs `place.image_url`, filtering on `is_active=True, status="active"` — which **includes draft OSM places** (draft affects `is_published`, not operational `status`). So a draft place can get a synced `image_url` before publication. Not a public leak (catalog hides drafts), but image moderation is bypassed for the auto-approve path. → TECHNICAL DEBT.

**Are image selection rules aligned between backend, scoring and frontend?** Backend public images = `{approved, active}`; frontend `PlaceCard` uses `verifiedImageUrl(place)` with `photoStateLabel` honesty badge (per `place_route_ui_data_contract.md`). Mostly aligned, but `place.image_url` denormalization can drift from `place_images` rows. → REQUIRES VERIFICATION on drift frequency.

---

## 9. Verification Lifecycle

**Two parallel verification mechanisms — inconsistent audit. REAL DEFECT (audit gap).**

| Path | Endpoint | Service | Audit log? |
|---|---|---|---|
| Admin "verify place" | `POST /admin/places/{id}/verify` | `admin_service.py::verify_place` | ✅ writes `verify_place` |
| Admin "place-verifications verify" | `POST /admin/place-verifications/places/{id}/verify` | `place_verification_service.py::apply_place_verification` | ❌ no audit |
| Admin "confirm-nearby" | `POST /admin/place-verifications/places/{id}/confirm-nearby` | `confirm_place_nearby`→`apply_place_verification` | ❌ no audit |
| **Public** confirm/reject | `POST /v1/verification/place/{id}/confirm` and `/reject` (`routers/verification.py`) | `apply_place_verification` | ❌ no audit, **no auth** |

`apply_place_verification` writes the `PlaceVerification` row but does **not** call `write_admin_audit_log`. The public `/v1/verification/*` write endpoints have neither auth nor admin audit. → REAL DEFECT (unauthenticated writes) + TECHNICAL DEBT (audit gap).

Scheduled re-verification: `place_verification_scheduler_service.py` + `POST /place-verification/enqueue-stale/{city}` (now admin-protected + audited, P0-2A).

---

## 10. Address Lifecycle

- At import: `import_city_osm.py::_address()` reads OSM `addr:*` tags (often missing).
- Backfill: `data/scripts/backfill_missing_place_addresses.py::reverse_geocode()` → **Nominatim** (real HTTP, rate-limited `--sleep 1.1`), runs automatically in `docker-compose.yml` `address-backfill` service with `--limit 1000 --apply`.
- Route start geocoding: `services/geocoding_service.py` uses **Geoapify** (returns `None` without `settings.geoapify_api_key`) — different provider, used for route start only, NOT place addresses.

**Are address fields reliably shown in UI?** `PlaceCard.tsx` renders `place.address` with a `MapPin` icon when present; empty address simply renders nothing. OSM places without `addr:*` tags depend on the backfill job having run. → PARTIALLY IMPLEMENTED (depends on backfill cadence; no UI fallback text).

---

## 11. Delete / Archive / Hide Behavior

No hard delete in the pipeline (aligns with AGENTS.md rule 17). "Removal" = hide:
- `place_import_lifecycle_service.py::hide_place` / `mark_missing_place` (after 3 missing OSM observations → `status="removed_from_source"`).
- `cleanup_bad_places.py` / `cleanup_imported_places_quality.py`: `is_active=False`, `status="hidden"`.
- `services/place_service.py::delete_place` exists (hard `db.delete`) but is not wired into admin routers. → REQUIRES VERIFICATION (is it reachable?). If unreachable, INTENTIONALLY DEFERRED.

---

## 12. Frontend Place Display

- List: `pages/places/PlacesListPage.tsx` → `PlaceCard.tsx` (image+honesty badge, category chip, title, address, description, up to 3 feature tags, hours/visit/price facts).
- Detail: `pages/places/PlaceDetailPage.tsx` shows facts + **admin moderation buttons inline on a public page** (POST `/admin/place-images/*`, `/admin/place-verifications/*` with `reviewer:'local-ui'`). These calls have no `Authorization` header → will 401 once `ADMIN_API_TOKEN` is enforced. → REAL DEFECT (broken admin actions + role confusion on public page).
- No map view anywhere (no Leaflet/Google/2GIS/Yandex). Coordinates shown as text. → PARTIALLY IMPLEMENTED vs competitors.

---

## 13. Tests Coverage

Present: `tests/test_place_import_visibility_new.py` (draft/publish/unpublish/catalog/route-candidate), `test_place_filters_service.py`, `test_place_image_review_service.py`/`_router.py`, `test_place_verification_service.py`/`_router.py`, `test_place_seed_*` (~25), `test_candidate_*`.

Gaps:
- No test asserting `is_route_eligible=False` removes a place from routes (because it doesn't — and no test catches it). → REAL DEFECT (untested + broken).
- No test for `is_searchable` (dead field).
- No test for `apply_place_verification` audit (because there is none).
- No test for `enrich_place_images.py` auto-approve on draft places.

---

## 14. Lifecycle Risks

| # | Risk | Class | Evidence | Impact |
|---|---|---|---|---|
| L1 | `is_route_eligible` not enforced in retrieval | REAL DEFECT | `candidate_retrieval_service.py:41-48` vs `place_public_visibility.py:36` | Admin cannot exclude a place from routes |
| L2 | `is_searchable` write-only dead field | REAL DEFECT | grep: no read in services/routers | False control; confusing admin UI |
| L3 | Public unauth verification writes | REAL DEFECT | `routers/verification.py` `/v1/verification/place/*` | Anyone can mutate verification state |
| L4 | `apply_place_verification` no audit | TECHNICAL DEBT | `place_verification_service.py:99-204` | No accountability for one verify path |
| L5 | Two verify paths diverge | TECHNICAL DEBT | `admin_service.verify_place` vs `apply_place_verification` | Inconsistent state + audit |
| L6 | Image auto-approve on draft places | TECHNICAL DEBT | `enrich_place_images.py` filter `status="active"` | Bypasses moderation pre-publish |
| L7 | 6 publication fields, no SoT | TECHNICAL DEBT | `models/place.py:40-44` | Drift, redundancy |
| L8 | `publication_status` not used in filters | PARTIALLY IMPLEMENTED | grep: only booleans filter | Documented SoT is not the real SoT |
| L9 | Admin buttons on public page lack auth header | REAL DEFECT | `PlaceDetailPage.tsx` | 401 after token enforcement |
| L10 | `delete_place` hard delete reachable? | REQUIRES VERIFICATION | `place_service.py:143` | Possible irreversible delete |

---

## 15. Recommended Backlog

**P0**
- **PL-1 (L1):** Make route retrieval call `public_route_place_conditions()` (or add `_true_or_null(Place.is_route_eligible)` to the route query) so `is_route_eligible` is enforced. Files: `services/candidate_retrieval_service.py`. DoD: test proving `is_route_eligible=False` removes place from candidates; diagnostics count matches retrieval. Size S.
- **PL-2 (L3):** Protect or remove `POST /v1/verification/place/{id}/confirm|reject`. Files: `routers/verification.py`. DoD: 401 without token or endpoint removed; test. Size S.

**P1**
- **PL-3 (L2):** Either enforce `is_searchable` in `get_places` search path or document it as reserved/remove from admin write set. Files: `services/place_service.py`, `schemas/admin.py`. DoD: field read or explicitly marked reserved in `place_visibility.md`. Size S.
- **PL-4 (L4/L5):** Add `write_admin_audit_log` to `apply_place_verification`; converge the two verify paths. Files: `services/place_verification_service.py`. DoD: audit row on every verify; test. Size M.
- **PL-5 (L9):** Remove admin moderation buttons from public `PlaceDetailPage` (move to admin shell) or gate behind token. Files: `frontend/src/pages/places/PlaceDetailPage.tsx`. Size M.

**P2**
- **PL-6 (L6):** Make `enrich_place_images.py` route candidate images to `needs_review` instead of auto-approve, or restrict to published places. Size M.
- **PL-7 (L7/L8):** Introduce a derived publication helper (single function computing public/route/search visibility from `publication_status`) without a data migration yet. Size M.

**P3**
- **PL-8 (L10):** Verify and gate/remove `delete_place`. Size S.
- **PL-9:** Unify `category` (string) and `category_id` (FK). Size L.

---

## 16. Next Implementation Prompt

```
Implement PL-1 + PL-2 from docs/audits/01_place_lifecycle_audit.md (route eligibility enforcement + close public verification writes).

Scope:
- services/candidate_retrieval_service.py: route retrieval must enforce is_route_eligible
  (use public_route_place_conditions() or add _true_or_null(Place.is_route_eligible)).
- routers/verification.py: protect POST /v1/verification/place/{id}/confirm|reject with admin_required
  from core/admin_auth.py (do NOT create a second auth system), or remove if unused — verify callers first.

Constraints: do not change the Place model, do not run a data migration, do not touch published-place behavior.

Tests (suffix _new):
- imported draft place still excluded from candidates.
- published place with is_route_eligible=False is excluded from candidates.
- diagnostics route-visible count equals actual retrieval count for a fixture city.
- /v1/verification confirm/reject returns 401 without token, 200/expected with token.

Docs: update docs/architecture/place_visibility.md route-eligibility section and docs/architecture/security.md endpoint table.

Analyze before changing. Report changed files, tests run, residual risks in one block.
```
