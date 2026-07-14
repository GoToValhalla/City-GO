# Publication state invariants

This document fixes boundaries between product publication state, import operational state, quality state and manual review state.

## City product state

Product publication state fields:

- `City.is_active`
- `City.launch_status`

Only these flows may change them:

- `services/admin_city_publication_service.py` — explicit city publish/unpublish;
- `scripts/repair_publication_states.py` — explicit repair action with dry-run/apply;
- future explicit admin actions, only with audit/reason and invariant tests.

These flows must not change City product state:

- import jobs;
- enrichment jobs;
- snapshot refresh;
- admin overview/read endpoints;
- publication reconciliation by default;
- quality/readiness scoring;
- Telegram moderation.

Import status `failed/partial/stale/running` is operational state. It must not turn a published city into draft/hidden/unpublished.

## Place publication state

Publication state fields:

- `Place.is_active`
- `Place.is_published`
- `Place.is_visible_in_catalog`
- `Place.is_route_eligible`
- `Place.is_searchable`
- `Place.publication_status`

Published place must not be reset to draft/hidden/rejected by import/enrichment/reconciliation. Unpublishing is allowed only through:

- explicit admin action;
- explicit destructive policy with reason/audit;
- repair script with explicit flag.

Import/enrichment/backfill may improve raw/data-quality fields, but must not disable already published flags.

## Manual review state

Manual queue includes only explicit manual cases:

- `publication_status in ('needs_review', 'needs_manual_review', 'deferred')`;
- or `review_queue_items.status='open'` for explicit manual review.

These are not manual queue by default:

- `draft`;
- `auto_backlog`;
- `low_confidence`;
- missing photo;
- missing address;
- low confidence without conflict/high-risk reason.

Telegram moderation uses only manual queue. If manual queue is empty, the bot returns `Очередь пуста` and does not pull draft/backlog.

## Auto backlog

Auto backlog is for deterministic policy, enrichment and backfill. It must not become a manual task for 17k places.

Trusted auto publish is allowed if a place:

- is `draft/auto_backlog/low_confidence`;
- has coordinates;
- has address;
- has official/site/provider official `address_source`;
- has `address_confidence >= 0.85`;
- has `quality_score >= 65`;
- is not closed/inactive/spam;
- is not duplicate suspected;
- has catalog/route eligible category.

Missing photo must not block trusted auto publish. It is a separate data-quality/enrichment task.

## Admin statistics semantics

- `Требуют проверки` = only manual review queue.
- `Не проверено авто` = auto backlog.
- `Низкая уверенность` = quality bucket, not manual queue.
- `Ошибка импорта` = operational import problem, not product hidden state.
- `Активные города` = `City.is_active=true AND City.launch_status='published'`.

## Source of truth chain before every fix

Before changing any endpoint/service/test fixture in admin/import/publication/review/Telegram, check and record the actual chain:

```text
router -> service -> model/table -> status field -> tests
```

Rules:

1. Do not change an endpoint based on a similarly named model.
2. Do not write a test fixture before checking which table the service actually reads.
3. If the chain contains a legacy artifact from `docs/architecture/legacy_code_register.md`, it must not be used as source of truth.
4. For `/admin/place-change-reviews/*`, the active chain is:

```text
routers/admin_place_change_review.py
  -> services/place_change_review_service.py
  -> ReviewQueueItem
  -> field_name='place_change'
  -> status='open'
```

5. `PlaceChangeReview` / `place_change_reviews` is legacy and must not be used in new endpoint tests or services.

## Protected invariants

Protected by code and tests:

1. Failed/partial import does not unpublish a published city.
2. Import/enrichment/reconciliation does not unpublish a published place.
3. Publication reconciliation does not perform destructive bulk reset without explicit destructive flag and reason.
4. Manual moderation does not show draft/auto_backlog/low_confidence.
5. Admin overview separates manual review, auto backlog and quality buckets.
6. Repair scripts use dry-run by default and write snapshot/report before apply.
7. Active endpoint tests do not use legacy source-of-truth models instead of the actual router/service/model chain.

## City product state guard: implementation note (2026-07-14)

`models/city.py` enforces invariant #1 via SQLAlchemy `set` event listeners
on `City.launch_status` / `City.is_active` that block any write moving away
from `"published"` unless the caller is `services/admin_city_publication_service.py`,
`scripts/repair_publication_states.py`, or explicitly calls
`allow_city_product_state_change(city)`.

This guard has one sharp edge: SQLAlchemy expires ORM attributes after every
`db.commit()`. A function that commits and only afterwards reassigns
`launch_status`/`is_active` — without reading the attribute again first —
causes the event to fire with `oldvalue = NO_VALUE` instead of the real
persisted value, which silently defeats the `oldvalue == "published"` check.
This is exactly the shape of any multi-step pipeline function (several
`db.commit()` calls interleaved with progress updates, then a final status
write) — `services/import_pipeline/enrichment_only.py` is the confirmed
real-world case (Arkhangelsk incident, 2026-07-14).

The guard now resolves the true committed value via `sqlalchemy.inspect(...)`
whenever `oldvalue` is `NO_VALUE`, instead of trusting the event payload
blindly. Any new automatic write path added later is protected by
construction — this is not something each caller needs to remember.
Regression coverage: `tests/test_city_publication_state_protection_new.py`.
