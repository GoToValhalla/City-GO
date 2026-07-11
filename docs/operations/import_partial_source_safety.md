# Import Partial-Source Safety Contract

## Incident signal

An all-city APPLY refresh completed with 10 scope errors (`429`, `504`, and an OSM raw-object overflow) while the report also showed large address deltas, source-missing counts, and hidden-place counts.

Repository inspection found three concrete unsafe contracts:

1. optional OSM fields such as `address` could overwrite known-good values with `None`;
2. any rejected normalized object could hide an existing place, even when rejection only meant unsupported taxonomy, missing coordinates, or an unusable name;
3. source-presence reconciliation had no durable profile ownership, so absence could not be proven independently for overlapping or historically changed profiles.

The OSM fetch path already raises on HTTP failures and raw-object overflow before `_apply_import`; this patch does not convert those failures into empty successful payloads.

## Required invariants

- A failed fetch, timeout, rate limit, malformed response, or raw-object overflow never enters APPLY reconciliation.
- Existing non-empty optional fields are preserved when the incoming value is `None`, blank, or absent.
- Only explicit lifecycle evidence (`source_closed`, `source_temporarily_closed`, `source_removed_from_source`) may automatically hide an existing place during rejected-object processing.
- Missing-source reconciliation is restricted to the exact successfully fetched source profile.
- Legacy presence rows without profile ownership are skipped fail-closed until a successful observation assigns them to a profile.
- OSM objects shared by multiple profiles have independent presence rows and independent missing counters.
- The migration is additive and reversible.

## Data model

`place_source_presence.source_profile` stores the profile that produced the presence row.

Existing rows are left `NULL`. They are not treated as authoritative for absence. On the next successful observation, one legacy row for that OSM object is claimed by the active profile. If another profile also returns the same object, a second profile-specific presence row is created.

## Reconciliation eligibility

Reconciliation runs only after:

1. the Overpass request returned successfully;
2. JSON parsing completed;
3. the response remained within `MAX_RAW_OBJECTS`;
4. normalization completed;
5. the current profile context is available.

Only rows matching all of the following are candidates:

- the current import scope;
- `source_type = osm`;
- `source_profile = current profile`;
- `source_external_id` absent from the complete current response.

## Preserve-known-good merge

For `address`, `opening_hours`, `website`, and `phone`:

- non-empty incoming value: eligible for the normal diff/review flow;
- `None`: preserve existing value;
- blank string: preserve existing value;
- absent field: preserve existing value.

Explicit deletion semantics are not accepted automatically in Stage 0.

## Rollout

1. Run focused tests and Alembic upgrade/downgrade tests.
2. Run one full CI on the branch.
3. Merge only after CI and review.
4. Deploy once and run production smoke.
5. Do not run an all-city APPLY immediately.
6. First run one bounded city/profile import and verify:
   - address count does not fall because of null input;
   - non-lifecycle rejected objects do not hide existing places;
   - `missing_from_source` only concerns the active profile;
   - legacy unscoped rows are reported as skipped, not missing.

## Kill criteria

Stop further APPLY runs if any of these occurs:

- an HTTP/source failure is followed by missing-source or hidden mutations;
- a known-good address is cleared by null/blank input;
- a taxonomy/name/coordinate rejection hides an existing public place;
- a profile updates missing counters owned by another profile;
- a legacy unscoped presence row is treated as authoritative absence.
