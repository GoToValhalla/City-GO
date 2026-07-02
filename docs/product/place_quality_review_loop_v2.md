# City GO — Place Quality and Review Loop v2

Date: 2026-07-02
Status: implementation contract
Roadmap: Phase 2 — Place Quality and Review Loop

## Goal

Reduce manual chaos and improve public quality by making the admin review loop explicit, gated and testable.

This phase does not replace the existing active workflow based on `ReviewQueueItem` and `services/place_change_review_service.py`. It adds the shared contract layer used by quality dashboard v2, review queue v2 and candidate-specific actions.

## Scope

- quality dashboard v2;
- review queue v2;
- candidate evidence view;
- approve/reject/defer actions;
- duplicate/conflict handling;
- photo approval flow.

## Existing implementation reused

The existing source of truth for field/place review remains:

- `models.review_queue_item.ReviewQueueItem`;
- `services.place_change_review_service`;
- `models.data_quality.DataQualityIssue`;
- `models.data_quality.DataQualityCandidate`;
- `models.place_photo_candidate.PlacePhotoCandidate`.

Legacy `models.place_change_review.PlaceChangeReview` remains historical compatibility only and must not be used for new review-loop work.

## New service contract

Implemented in `services/admin_quality_review_loop_service.py`.

### Dashboard

`build_quality_dashboard_v2()` returns:

- open review count;
- publication blockers;
- duplicate candidate blockers;
- conflict candidate blockers;
- photo candidate blockers;
- next admin actions.

The dashboard blocks publication when there are open reviews or publication-blocking issues.

### Review actions

Supported actions:

- `approve`;
- `reject`;
- `defer`.

Rules:

- unsupported actions are rejected;
- terminal items cannot be acted on again;
- deferred items cannot be deferred again;
- every action returns a deterministic next status and resolution;
- buttons must be disabled after the action is applied.

### Evidence view

`build_candidate_evidence_view()` returns:

- item kind;
- item id;
- place id;
- evidence payload;
- proposed patch;
- missing evidence fields;
- duplicate/conflict safety flag;
- photo review flag.

Evidence is considered incomplete unless source, reason and confidence are present.

### Review queue pagination and filters

`build_review_queue_page()` defines stable pagination:

- `limit` between 1 and 100;
- non-negative `offset`;
- stable sort contract: `created_at`, `id`;
- explicit `has_next` and `next_offset`.

`assert_review_queue_filters_supported()` allows only explicit filters:

- `city_slug`;
- `category`;
- `status`;
- `severity`;
- `item_kind`;
- `route_eligible`;
- `has_photo`.

## Test coverage

Covered in `tests/test_admin_quality_review_loop_service.py`:

- dashboard blockers and next actions;
- clean dashboard allows publication;
- approve/reject/defer only for actionable items;
- repeated completed actions are blocked;
- defer cannot be repeated;
- action result disables the action button;
- photo candidate approve/reject lifecycle;
- candidate evidence and missing evidence;
- duplicate/conflict safety review flag;
- stable pagination;
- explicit filter allow-list.

## Exit criteria

- admin sees what blocks publication;
- candidate approval writes deterministic review decision state;
- no repeated enabled buttons after completed action;
- queue pagination and filters are stable;
- documentation exists in repo and Confluence;
- tests exist;
- CI is green.
