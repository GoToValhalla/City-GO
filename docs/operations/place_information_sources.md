# Place Information Sources

City GO uses a source-first pipeline: collect place entities, preserve raw observations, enrich missing fields, calculate field confidence and publish only data that passes quality rules.

## Unified Run

The admin action `Собрать и обогатить` now starts one background job:

```text
OSM discovery by enabled scopes
→ upsert and deduplication
→ addresses, photos and category normalization
→ Geoapify, Wikidata and official-site enrichment
→ confidence and conflict review
→ publication decisions
→ quality and readiness
```

The job is queued through `POST /admin/place-enrichment/pipeline/{city_slug}/run` and executed by `import-worker`.

## Discovery Sources

### OSM / Overpass

OSM is the current source for discovering places that do not yet exist in City GO.

- Collection uses enabled `city_import_scopes`.
- Repeated runs can find newly created or previously missed OSM objects.
- Imported entities go through upsert and deduplication before enrichment.
- If a required district or nearby territory is absent from scopes, it will not be searched.

Geoapify and Wikidata currently enrich known coordinates/entities. They are not yet configured as independent city-wide discovery collectors.

## Enrichment Sources

### Geoapify Places API

Enabled by `GEOAPIFY_API_KEY`.

- Address, website, phone and opening hours near existing coordinates.
- Stored as `SourceObservation.source_type = "geoapify"`.
- Only missing public fields are filled automatically.

### Wikidata / Wikimedia Commons

- Cultural objects, landmarks, official websites, factual descriptions and Commons photo candidates.
- Stored as `SourceObservation.source_type = "wikidata"`.
- Weak title matches are ignored.

### Official Website Metadata

- Uses an existing website/source URL or a URL found by Geoapify/Wikidata.
- Reads HTML metadata, Open Graph and JSON-LD/schema.org.
- Extracts descriptions, phone, opening hours and photo candidates.
- Stored as `SourceObservation.source_type = "official_site"`.

### City GO Category Rules

- Adds safe generic `atmosphere`, `inside` and `best_for` sections when missing.
- Does not invent addresses, contacts, ratings or opening hours.

## Field Policy

The pipeline can fill missing values for:

- `address`
- `website`
- `phone`
- `opening_hours`
- `short_description`
- `atmosphere`
- `inside`
- `best_for`

Conflicting non-empty values are preserved and added to `review_queue_items` with `reason = "source_conflict"`.

Photo URLs are saved as candidates. They do not silently replace the primary photo.

Missing fields after enrichment are queued with `reason = "missing_after_enrichment"`.

## Provider Policy

Yandex Maps, 2GIS and Google can be used for map UI or outbound links where their terms permit it. Their proprietary place databases, reviews, ratings and photos must not be scraped or persisted without a suitable licence/API plan.

## Runtime Configuration

```env
GEOAPIFY_API_KEY=
PLACE_ADDRESS_GEOCODER_USER_AGENT=CityGoAddressBackfill/1.0
```

Without a Geoapify key, OSM collection, Wikidata/Wikimedia, official-site metadata and City GO rules continue to work.

## Operational Check

After one city run, inspect:

- places found and saved;
- `source_observations` by provider;
- fields enriched and provider errors;
- `place_field_confidence`;
- `place_photo_candidates`;
- `review_queue_items`;
- city readiness and route eligibility.

Next data expansion: add licensed regional open-data and tourism-portal collectors as additional discovery sources before enrichment.
