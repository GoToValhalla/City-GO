# 06 — Data Pipeline Deep Audit

> Due diligence of ingestion, enrichment, validation, cleanup and publication. No code changed. Concrete script/service references.
> Classification: REAL DEFECT · TECHNICAL DEBT · PARTIALLY IMPLEMENTED · FUTURE ROADMAP · INTENTIONALLY DEFERRED · REQUIRES VERIFICATION

---

## 1. Executive Summary

City Go has **two parallel OSM ingestion branches** that are not unified: a production DB importer (`data/scripts/import_city_osm.py`, writes `Place` directly, draft by P0-4) and an offline Zelenogradsk seed builder (`osm_seed_builder.py` → JSON → API `POST /place-seed/import/`), each with a **different taxonomy map**. Publication safety is correct after P0-4 (OSM + seed write create drafts; dev seed publishes explicitly). Addresses are backfilled via **real Nominatim**; route-start geocoding uses **Geoapify** (different provider, returns None without key).

Main issues:

1. **`POST /place-seed/import/` is unauthenticated** (`routers/place_seed_import.py`) — a public mass-write path used by `scripts/production_place_import.py --real`. → REAL DEFECT (security).
2. **Production cron is not wired** — `run_due_import_jobs.py` is the documented orchestrator but is absent from `docker-compose.yml`/CI; only `seed` and `address-backfill` run automatically. → TECHNICAL DEBT (manual-only imports).
3. **Dangerous scripts lack tests** — `cleanup_imported_places_quality.py`, `cleanup_bad_places.py` (`run`/`--apply`), `backfill_missing_place_addresses.py`, `enrich_place_images.py` (auto-approve) can mass-mutate data with no test coverage. → TECHNICAL DEBT / data-risk.
4. **`load_seeds.py` is dead/broken** against the current `Place` model (`name`/`active` invalid kwargs; string ids). → TECHNICAL DEBT (cleanup).
5. **Two taxonomies** (`import_city_osm._category()` vs `osm_seed_builder.TYPE_TO_CATEGORY`) + a legacy non-canonical one (`transform_osm_zelenogradsk.py`). → TECHNICAL DEBT.

No hard delete exists anywhere (aligns with AGENTS.md rule 17) — all removals are hide/deactivate.

---

## 2. Data Sources Map

| Source | Collected by | Lands in | Production? |
|---|---|---|---|
| OSM Overpass | `import_city_osm.py::_fetch_osm_objects()` | PostgreSQL (`Place`/`SourceObservation`/`PlaceSourcePresence`) | ✅ primary |
| OSM Overpass (Zelenogradsk) | `collect_osm_zelenogradsk.py::collect_places()` | `data/raw/...json` + `data/seeds/place_import/...json` | seed prep |
| Seed JSON (canonical) | `data/seeds/place_import/*.json` | API `POST /place-seed/import/` → `import_place_seed_items()` | ✅ via `production_place_import.py` |
| Editorial seed | `zelenogradsk_editorial_walks.json` (`source:"tourist_page"`) | same API | manual refresh |
| Legacy places JSON | `data/seeds/places/zelenogradsk.json` | `load_seeds.py` | **dead/broken** |
| Dev inline | `scripts/seed_minimal_data.py::SEED_DATA` | PostgreSQL (published) | docker `seed` |
| FE static catalog | `frontend/public/data/zelenogradsk_places.json` | image pipeline (not DB) | static UI |

---

## 3. Import Scripts Map

| Script | Purpose | Production? | Idempotent? | Invocation |
|---|---|---|---|---|
| `import_city_osm.py` | scoped OSM → DB | ✅ | ✅ (match source_url→slug) | cron script / manual |
| `run_due_import_jobs.py` | orchestrator (import+cleanup+backfill) | documented | ✅ (delegates) | **manual/server cron, NOT in docker/CI** |
| `import_target_cities.py` | wrapper → orchestrator `--force` | manual | ✅ | manual |
| `import_cron_config.py` / `import_cron_db.py` | target selection + DB locking | support | lock-based | imported by cron |
| `production_place_import.py` | HTTP client → seed import API | ✅ | ✅ (slug dedup) | manual |
| `seed_minimal_data.py` | dev multi-city seed (published) | dev | ✅ get_or_create | **docker `seed`** |
| `backfill_missing_place_addresses.py` | Nominatim reverse geocode | ✅ | partial | **docker `address-backfill --limit 1000 --apply`** |
| `collect/fetch/transform_osm_zelenogradsk.py` | offline OSM→seed | prep / legacy | overwrite | manual |
| `osm_seed_builder.py` | build canonical seed items | ✅ (prep+tests) | slug dedup | imported |
| `cleanup_bad_places.py` / `cleanup_imported_places_quality.py` | mass hide | maintenance | n/a | manual `--apply` |
| `backfill_place_confidence.py` | confidence backfill | maintenance | n/a | manual |
| `enrich_place_images.py` | DB image enrich (auto-approve) | maintenance | n/a | manual `--apply` |
| `enrich_catalog_images.py` / `image_pipeline/run.py` | FE static catalog images | maintenance | overwrite | `refresh_place_images.py` |
| `check_import_status.py` / `city_coverage_report.py` / `seed_stats.py` / `validate_*` | read-only reporting/validation | tooling | read | manual |
| `review_places.py` / `transform_osm_zelenogradsk.py` / `load_seeds.py` | legacy | **dead** | — | — |

Docker wiring (`docker-compose.yml`): only `seed` (`seed_minimal_data.py`) and `address-backfill` run automatically. No OSM import, no `run_due_import_jobs`, no `production_place_import`. CI (`.github/workflows/deploy.yml`) inherits these two.

---

## 4. Seed Data Map

| File | Format | Model-compatible? | SoT or artifact | Keep/Archive |
|---|---|---|---|---|
| `data/seeds/cities.json` | legacy (`lat`/`active` not on City) | ❌ | artifact | Archive |
| `data/seeds/places/zelenogradsk.json` | legacy (`name`/`active`/`_needs_review`) | ❌ | artifact | Archive |
| `data/seeds/place_import/zelenogradsk_osm.json` | canonical `{items:[PlaceSeedItem], dry_run}` | ✅ | source-of-truth seed | Keep |
| `data/seeds/place_import/zelenogradsk_editorial_walks.json` | canonical editorial | ✅ | SoT | Keep |
| `data/raw/zelenogradsk_osm.json` | Overpass raw | n/a | artifact | Keep (regenerable) |
| `data/enrichment/*.json` | enrichment + verification queue | n/a | artifact | Keep |
| `data/config/import_targets.json` | 5 cities × 3 scopes | ✅ | config | Keep |

---

## 5. OSM Pipeline Review

Production path:
```
import_targets.json → run_due_import_jobs._run_target()
  → import_cron_db.lock_target()
  → import_city_osm.run(): _bbox(scope) → _fetch_osm_objects() → _normalize_osm_object()
     → _apply_import(): SourceObservation, Place(draft if new), apply_accepted_import_to_place (existing),
        _mark_missing_sources() [hide after 3 misses], _hide_bad_existing_places()
  → cleanup_imported_places_quality.run() [optional]
  → backfill_missing_place_addresses.run() [optional]
  → import_cron_db.schedule_next()
```
Profiles `PROFILE_FILTERS` + `services/import_profiles.py::production_profile()` block `full_osm`. Pre-flight guards: unknown city/scope, disabled scope, `MAX_RAW_OBJECTS=2500`, non-production profile → `SystemExit`. Overpass timeout 60s.

**Re-import nuance:** `apply_accepted_import_to_place()` does NOT change `is_published`/`publication_status` but sets `is_active=True`, `status="active"`. Draft stays catalog-invisible but becomes operationally active. → INTENTIONALLY DEFERRED (correct, but document it).

Offline path duplicates ingestion with a different taxonomy → see §8.

---

## 6. Address Pipeline Review

| Path | Provider | Function | Real? |
|---|---|---|---|
| Import-time | OSM tags | `import_city_osm._address()` | from tags |
| Backfill | **Nominatim** | `backfill_missing_place_addresses.reverse_geocode()` | ✅ real HTTP, rate-limited |
| Route start | **Geoapify** | `geocoding_service.geocode()` (`:24-27`) | ✅ real, None without key |

Two providers for two purposes. Backfill runs automatically in docker with `--limit 1000 --apply` → mass address overwrite without test coverage. → TECHNICAL DEBT.

---

## 7. Image Pipeline Review

Three tracks:
1. **FE static catalog** — `data/scripts/image_pipeline/*` (wikidata→commons→og→mapillary→rules selector), entry `scripts/refresh_place_images.py`. Writes `frontend/public/data/...json` + `data/enrichment/*`. `--live` toggles network.
2. **Rules-only** — `enrich_catalog_images.py` duplicates the non-live path. → TECHNICAL DEBT (duplication).
3. **DB place images** — `enrich_place_images.py::run()` builds `PlaceImage` from `SourceObservation` OSM tags and **auto-approves** (`status=approved`, `is_primary=True`, syncs `place.image_url`), filtering `is_active=True, status="active"` — **includes draft places**. → TECHNICAL DEBT (moderation bypass; cross-ref File 01 L6).

Validation: `validate_catalog_images.py::validate_catalog()` (schema checks on static JSON).

---

## 8. Taxonomy Review

| Layer | Mechanism | Canonical? |
|---|---|---|
| Seed import (API) | `place_seed_validation_service` → `place_taxonomy_service` | ✅ canonical |
| OSM direct import | inline `import_city_osm._category()` | ❌ separate map |
| Offline seed builder | `osm_seed_builder.TYPE_TO_CATEGORY` | ❌ separate map |
| Legacy transform | `transform_osm_zelenogradsk.OSM_TO_CATEGORY` (`restaurant`/`landmark`…) | ❌ non-canonical |
| Legacy validate_seeds | required fields only | ❌ no taxonomy |

Canonical validation lives in `place_taxonomy_diagnostics_service.py` + `place_taxonomy_service.py` but the **direct OSM importer bypasses it**. → TECHNICAL DEBT (category drift between branches).

---

## 9. Data Quality Risks

| # | Risk | Class | Evidence |
|---|---|---|---|
| D1 | `POST /place-seed/import/` unauthenticated mass write | REAL DEFECT | `routers/place_seed_import.py` |
| D2 | Cron orchestrator not in infra | TECHNICAL DEBT | `docker-compose.yml` lacks `run_due_import_jobs` |
| D3 | Dangerous scripts untested (cleanup/backfill/enrich) | TECHNICAL DEBT | tests/ grep |
| D4 | `enrich_place_images.py` auto-approves on draft places | TECHNICAL DEBT | filter `status="active"` |
| D5 | Two OSM taxonomies + legacy third | TECHNICAL DEBT | §8 |
| D6 | `load_seeds.py` broken/dead | TECHNICAL DEBT | invalid kwargs vs model |
| D7 | Duplicate image enrich paths | TECHNICAL DEBT | `enrich_catalog_images.py` vs `image_pipeline/run.py` |
| D8 | `source_*_service.py` bypassed by inline observation writes | TECHNICAL DEBT | `import_city_osm._save_source_observation` |
| D9 | Auto address overwrite in docker (`--limit 1000 --apply`) | REQUIRES VERIFICATION | `docker-compose.yml` |

---

## 10. Data Pipeline Backlog

**P0**
- DP-1 (D1): Protect `POST /place-seed/import/` with `admin_required`; update `production_place_import.py` to send the token. Files: `routers/place_seed_import.py`, `scripts/production_place_import.py`. DoD: 401 without token; importer passes token; test. Size S.

**P1**
- DP-2 (D3): Add tests for `cleanup_bad_places.run`, `cleanup_imported_places_quality.run`, `backfill_missing_place_addresses.run` (dry-run vs apply). Size M.
- DP-3 (D4): Make `enrich_place_images.py` enqueue `needs_review` instead of auto-approve, or restrict to published places. Size M.
- DP-4 (D2): Wire `run_due_import_jobs.py` as a scheduled job (compose profile / external cron doc + Make target). Size M.

**P2**
- DP-5 (D5): Route the direct OSM importer through canonical taxonomy validation (`place_taxonomy_service`). Size M.
- DP-6 (D8): Use `source_observation_service` / `source_presence_service` in `import_city_osm` instead of inline writes. Size M.
- DP-7 (D7): Collapse `enrich_catalog_images.py` into `image_pipeline/run.py`. Size S.
- DP-9 (D9): Verify/limit auto address backfill in docker; gate behind explicit run. Size S.

**P3**
- DP-8 (D6): Archive `load_seeds.py`, `transform_osm_zelenogradsk.py`, `data/seeds/places/*` and `cities.json` to a legacy folder (move, not delete — AGENTS.md rule 17). Size S.

---

## 11. First Implementation Prompt

```
Implement DP-1 from docs/audits/06_data_pipeline_deep_audit.md (authenticate the seed import endpoint).

Scope:
- routers/place_seed_import.py: add Depends(admin_required) from core/admin_auth.py to POST /place-seed/import/.
  Do NOT create a second auth system.
- scripts/production_place_import.py: send Authorization: Bearer from an env var (e.g. ADMIN_API_TOKEN);
  follow secrets rule — request the env var name, do not read secret files directly.
- Verify the dry-run endpoint (/place-seed/dry-run) and validation endpoint policy; decide if they also need auth
  (dry-run writes nothing — may stay open; document the decision).

Constraints: do not change the import business logic, do not touch the route engine, do not touch telegram/frontend.

Tests (suffix _new): /place-seed/import returns 401 without token, succeeds with token (reuse admin auth bypass fixture).
Docs: update docs/architecture/security.md endpoint table and docs/production_data_refresh.md.

Analyze first, then implement. Report changed files, tests run, residual risks in one block.
```
