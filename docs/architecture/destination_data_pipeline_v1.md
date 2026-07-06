# Destination Data Pipeline + Operational Workspace v1

## Цель

Destination Data Pipeline v1 связывает уже существующий Destination-first foundation с реальным операторским потоком:

Destination + DestinationScope → backend-owned run → production OSM/Overpass candidates → Place create/upsert → DestinationPlaceMembership → enrichment task → `PlaceDataMergeService` safe apply или `ReviewItem` → readiness metrics → admin workspace → public `/places?destination_slug=...` и route candidates under feature flag.

## Основные сущности

- `DestinationDataPipelineRun` (`destination_data_pipeline_runs`) хранит статус, stage, scope ids, counters, errors, idempotency key, timestamps and dry-run flag.
- `DestinationPlaceMembership` остаётся материализованным read model для каталога и маршрутов.
- `ReviewItem`, `PlaceManualOverride`, lineage/version and sanitizer reused from Place Cards & Data Refresh v1.
- `EnrichmentTask` reused for deterministic enrichment proposals.

## Admin endpoints

Все endpoints защищены тем же `admin_required`, что и остальные `/admin/*`.

- `POST /admin/destinations/{slug}/data-pipeline/run`
- `GET /admin/destinations/{slug}/data-pipeline/latest`
- `GET /admin/destinations/{slug}/data-pipeline/runs`
- `GET /admin/destinations/{slug}/data-pipeline/runs/{run_id}`
- `POST /admin/destinations/{slug}/data-pipeline/runs/{run_id}/stop`
- `POST /admin/destinations/{slug}/memberships/recalculate`
- `POST /admin/destinations`
- `PATCH /admin/destinations/{slug}`
- `POST /admin/destinations/{slug}/scopes`
- `PATCH /admin/destinations/{slug}/scopes/{scope_id}`
- `DELETE /admin/destinations/{slug}/scopes/{scope_id}`
- `GET /admin/destinations/{slug}/readiness`
- `GET /admin/destinations/{slug}/review-items`

Write endpoints create admin audit log rows.

## Pipeline stages

1. `preparing`: validates destination and enabled scopes.
2. `importing`: OSM/Overpass adapter collects candidates from enabled scopes.
3. `enriching`: places missing address/description/hours/duration receive deterministic `EnrichmentTask`.
4. `merging`: merge is performed only by `PlaceDataMergeService`.
5. `recalculating_memberships`: bbox recalc updates materialized memberships and writes overlap conflicts.
6. `completed`: readiness metrics are recomputed.

## Counters

Runs expose:

- `scopes_total`, `scopes_processed`
- `candidates_found`
- `places_created`, `places_updated`, `duplicates_skipped`
- `memberships_created`, `memberships_updated`
- `review_items_created`, `enrichment_tasks_created`, `safe_merges_applied`
- `service_only_hidden`, `errors_count`

## Import and enrichment safety

- Repeated imports are idempotent by `city_id + slug`.
- Candidates outside bbox are ignored before write.
- Service-only categories are created hidden: `is_published=false`, `is_visible_in_catalog=false`, `is_route_eligible=false`, `internal_status=service_only`.
- Existing fields are not overwritten directly by workers.
- Missing-field enrichment uses `EnrichmentTask` → `PlaceDataMergeService`.
- Manual protected fields and conflicts create `ReviewItem`.

## Readiness metrics

`GET /admin/destinations/{slug}/readiness` aggregates admin-only metrics over materialized memberships:

- places, published places, route-eligible places, service-only hidden
- orphan places, memberships, pending reviews
- address/photo/description/category/coordinates/opening-hours coverage
- average completeness, readiness score, degraded sections
- latest pipeline run status/time

This is not used on the public hot path.

## Bootstrap readiness

The same readiness response includes:

- `bootstrap_ready`
- `bootstrap_blockers`

The admin UI disables collection until blockers are resolved:

- `NO_SCOPES`: no collection contours exist.
- `NO_ENABLED_SCOPES`: contours exist, but all are disabled.
- `INVALID_SCOPE_GEOMETRY`: at least one enabled contour has an invalid bbox.

## Admin workspace

`AdminDestinationDetailPage` now shows:

- summary/readiness cards
- run actions: full, import only, enrich only, membership recalc
- latest run status/stage
- coverage metrics and degraded sections
- memberships, orphan places, pending review items
- run history
- link to public catalog filtered by `destination_slug`

All new labels are Russian and machine status/reason codes are mapped to human-readable text.

## Feature flags

Rollout order:

1. `DESTINATION_FOUNDATION_ENABLED`
2. `DESTINATION_IMPORT_ENABLED`
3. `DESTINATION_CATALOG_READS_ENABLED`
4. `DESTINATION_ROUTE_READS_ENABLED`

Legacy `/places?city_slug=...` and city route payloads remain supported.

## Limitations

- Local v1 uses bbox fields and no PostGIS requirement.
- Tests can force `CITYGO_DESTINATION_SOURCE_ADAPTER=deterministic`; production default is `osm_overpass`.
- `places.city_id` remains non-null. For destinations without `legacy_city_id`, import resolves an existing active city whose center is inside the scope bbox; if none exists, the run is partial with an error counter.
- Stop endpoint can cancel queued/running rows; synchronous completed runs return `409`.
- External source adapters can be added behind `collect_scope_candidates` without changing admin/public contracts.

## Local verification

Backend targeted:

```bash
python -m pytest tests/test_destination_foundation_v1_new.py tests/test_destination_data_pipeline_run_new.py tests/test_destination_import_flow_new.py tests/test_destination_enrichment_flow_new.py tests/test_destination_membership_recalculation_new.py tests/test_destination_readiness_new.py tests/test_public_catalog_destination_pipeline_new.py tests/test_route_destination_candidates_new.py -q --no-cov
```

Frontend:

```bash
cd frontend && npm run lint
cd frontend && npm test -- --run
cd frontend && npm run build
```

## Production smoke checklist

1. `alembic upgrade head`
2. run destination backfill if not already run
3. `GET /health`
4. `GET /v1/destinations`
5. `GET /v1/destinations/{pilot_slug}`
6. `GET /places?destination_slug={pilot_slug}`
7. `POST /admin/destinations/{pilot_slug}/data-pipeline/run` with `{"mode":"full","dry_run":false}`
8. poll `GET /admin/destinations/{pilot_slug}/data-pipeline/latest`
9. `GET /admin/destinations/{pilot_slug}/readiness`
10. `GET /places?destination_slug={pilot_slug}` again
11. `POST /v1/user-routes/build` with destination payload
12. verify admin workspace metrics and run history

## Phone operator pilot: Куршская коса

1. Откройте `/admin/destinations`.
2. Создайте направление:
   - name: `Куршская коса`
   - slug: `kurshskaya-kosa`
   - type: `Туристический кластер`
3. Откройте страницу направления.
4. Добавьте контур:
   - code: `core`
   - name: `Основной контур`
   - profile: `Туристические места`
   - south: `54.94`
   - west: `20.43`
   - north: `55.32`
   - east: `20.99`
   - enabled: да
5. Убедитесь, что в готовности нет блокеров начальной настройки.
6. Нажмите `Собрать и обогатить места`.
7. После завершения откройте `Места направления` и публичный каталог.
