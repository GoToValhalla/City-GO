# Publication Policy v1

City GO has one public catalog. The website and Telegram bot must read the same published cities and the same published places. Publication is controlled by city publication state and place publication flags, not by separate web/bot rules.

## Product contract

1. A new city is not visible by default. It becomes public only after the admin publishes it.
2. A published city remains public until the admin unpublishes it.
3. A published place remains visible during imports, enrichment, address updates and photo updates.
4. Incoming changes never overwrite a published place directly when the change is critical.
5. Critical changes go to review with a diff. The old public version stays visible until the admin accepts or rejects the change.
6. Safe non-critical changes may be auto-accepted only when hard gates pass and trust score is high enough.
7. Auto-publication starts in shadow mode. Shadow mode records what the system would do, but does not change public flags.

## Tables

`place_publication_decisions` stores every policy decision:

- `mode`: `shadow` or `apply`.
- `decision`: `shadow_auto_publish`, `auto_publish`, `send_to_review`, `hidden`, `keep_published`.
- `trust_score`: score at decision time.
- `failed_gates`: hard gates that blocked publication.
- `review_reasons`: human-readable review categories.

`place_change_reviews` stores field-level diffs for incoming updates:

- `field_name`
- `old_value`
- `new_value`
- `reason`
- `source`
- `confidence`
- `trust_score`
- `status`: `pending`, `accepted`, `rejected`.

`place_snapshots` stores rollback snapshots before auto-publication or later critical transitions.

## Hard gates

A place must pass all hard gates before trust score can publish it:

- city is published and active;
- name is present and at least three characters;
- coordinates are valid;
- coordinates are inside city bbox when bbox is configured;
- category exists;
- public-hidden utility categories are blocked;
- spam and duplicate flags are not set;
- place is not closed or archived.

If any hard gate fails, the place goes to review or stays hidden depending on score. It is not auto-published.

## Trust score

The score is `0..100` and is intentionally conservative:

- existing `quality_score`: up to 40;
- photo/image: up to 15;
- description: up to 10;
- address: 8;
- opening hours: 7;
- source reliability: up to 20;
- source URL: 5;
- high confidence/verification: up to 15;
- expired critical field penalty: -20.

Default thresholds:

- `>= 90`: candidate for auto-publication;
- `60..89`: review queue;
- `< 60`: hidden/low quality review.

## Shadow mode

Nightly workflow runs in shadow mode by default:

```bash
python scripts/run_publication_policy.py --mode shadow --limit 500
```

Shadow mode records decisions and review queue items, but does not set:

- `is_published`;
- `is_visible_in_catalog`;
- `is_route_eligible`;
- `is_searchable`.

This lets admins compare system decisions against manual review before enabling real auto-publication.

## Apply mode

Apply mode requires two explicit controls:

```bash
python scripts/run_publication_policy.py \
  --mode apply \
  --auto-publish-enabled \
  --auto-publish-threshold 90
```

The GitHub workflow also refuses `apply` unless `auto_publish_enabled=true` is set in workflow inputs.

When a place is auto-published, the service:

1. writes a `place_snapshots` row;
2. sets canonical public flags on `places`;
3. records an applied `place_publication_decisions` row.

## Change review rules

Always manual review:

- name/title changes;
- category changes;
- location changes;
- existing address changes;
- closure/archive markers;
- any other critical field change.

Auto-acceptable fields, when apply mode is enabled and score is high enough:

- photo/image URL;
- website;
- phone;
- opening hours;
- short description;
- atmosphere/inside/best_for;
- quality score components.

Critical review keeps the published place visible with the old values. The incoming change is stored in `place_change_reviews` and linked into `review_queue_items`.

## Workflows

`Publication Policy` workflow:

- runs daily at `01:00 UTC` (`03:00 Europe/Paris` during summer time);
- can be launched manually;
- scheduled run is always shadow;
- manual run can target a single city;
- manual apply requires `auto_publish_enabled=true`.

## Operational rollout

1. Run shadow mode for at least 500 decisions.
2. Compare `shadow_auto_publish` decisions with admin decisions.
3. Enable apply for one city only.
4. Monitor review queue, public city count, public place count and rollback rate.
5. Enable apply for all published cities only after false positives are below 1%.
