# Data Foundation P1: Quality Scoring + City Readiness

## Place Quality Scoring

Service: `services/quality_scoring.py`.

`score_place_quality(place)` returns deterministic components:

| Component | Max | Source fields |
|---|---:|---|
| `completeness_score` | 40 | title, canonical/category, coordinates, address, hours, duration, price, basic attributes |
| `photo_score` | 25 | `image_url`, `Place.images` |
| `description_score` | 15 | `short_description` length |
| `confidence_score` | 10 | `existence_confidence_score` or `confidence` |
| `freshness_score` | 10 | `verified_at`, `last_verified_at`, `address_updated_at`, `updated_at`, `created_at` |

Tier thresholds:

| Tier | Rule |
|---|---|
| `gold` | score >= 80 |
| `silver` | score >= 55 |
| `bronze` | score >= 30 |
| `draft` | score < 30 |
| `rejected` | spam POI or rejected lifecycle |

`apply_place_quality_score(db, place)` persists score fields, recalculates `is_route_eligible`, writes `route_exclusion_reason`, and appends `QualityScoreHistory`.

## Route Eligibility Contract

Routes use `services.route_eligibility.route_eligible_sql_conditions()` and `evaluate_place_route_eligibility()`.

A route place must be public, active, published, visible, geocoded, non-spam, non-duplicate, not expired, not a forbidden category, and in an allowed quality tier.

P1 quality scoring evaluates route eligibility against the newly projected quality tier before persisting it, so a place promoted from `bronze` to `gold` can become route eligible in the same recalculation.

## City Readiness Snapshots

Service: `services/city_readiness/score.py`.

`recalculate_city_readiness_snapshot(db, city_slug=...)`:

1. loads all places for the city;
2. recalculates per-place quality scores by default;
3. computes readiness metrics;
4. inserts `CityQualitySnapshot`;
5. updates `City.readiness_score` and `City.quality_status`.

Readiness status:

| Status | Rule |
|---|---|
| `ready` | score >= 70, eligible places >= 30, coordinate coverage >= 90% |
| `needs_review` | score >= 40 |
| `not_ready` | score < 40 |

## Admin Endpoint

```http
POST /admin/routes/readiness/{city_slug}/recalculate
```

Optional JSON body:

```json
{
  "reason": "manual_recheck",
  "recalculate_place_scores": true
}
```

Response includes the normal readiness payload plus:

```json
{
  "snapshot_id": 123,
  "recalculated_places": 35
}
```

## Server Script

```bash
python scripts/recalculate_city_readiness.py --city zelenogradsk
python scripts/recalculate_city_readiness.py --all
python scripts/recalculate_city_readiness.py --all --skip-place-scores
```

`--skip-place-scores` rebuilds snapshots from existing `places.quality_*` fields without recalculating place quality first.

## Tests

Primary coverage:

```bash
python -m pytest tests/test_data_foundation_quality_readiness.py -q
```

Covers:

- complete place promoted to `gold` and route eligible;
- sparse place downgraded and excluded from routes;
- spam POI forced to `rejected`;
- SQL route eligibility filters;
- persisted city readiness snapshot recalculation;
- admin recalc endpoint.
