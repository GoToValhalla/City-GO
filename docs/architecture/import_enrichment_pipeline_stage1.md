# Unified Import / Enrichment Pipeline

Last updated: 2026-06-24

City GO uses one background pipeline for collecting missing places and enriching the city catalog. Import is diff-driven: unchanged places are not mutated; changed places and cities are moved to manual review.

## Admin Flow

1. Open `Обогащение данных` or the city workspace.
2. Select a city and click `Собрать и обогатить`.
3. Backend queues an `admin_city_import` job.
4. `import-worker` executes collection and enrichment.
5. Changed places are hidden from public surfaces and added to review.
6. A published city is unpublished only when real changes were found.
7. With zero changes, the city publication state remains unchanged.

## Complete Pipeline

```text
OSM scopes
→ source diff
→ update only changed/new places
→ reverse-geocode missing addresses
→ collect photo candidates
→ normalize taxonomy
→ external-source enrichment
→ confidence and conflicts
→ manual review
→ readiness
```

## Address Enrichment

Address enrichment uses a legal cached provider cascade:

1. Structured OSM address tags already attached to the source object.
2. Geoapify Reverse Geocoding when `GEOAPIFY_API_KEY` is configured.
3. Nominatim as a low-rate fallback.

The selected candidate stores:

- normalized Russian address;
- provider in `address_source`;
- confidence in `address_confidence`;
- update time in `address_updated_at`;
- precision (`building`, `street`, or `locality`) in operation output.

Rules:

- venues require at least street-level data;
- outdoor objects may use `Рядом с <улица>` or a locality label;
- city-only results are not presented as exact venue addresses;
- conflicting existing addresses go to review and are not overwritten;
- an enriched address moves the place to `needs_review`;
- all provider responses are cached;
- provider errors do not erase existing data.

Geoapify currently provides a free allowance of 3000 credits per day and is the primary practical bulk provider. The public Nominatim service is only a fallback: its policy requires caching and heavily restricts recurring bulk jobs. Yandex free geocoder results cannot be stored in the City GO database. 2GIS requires a demo key or subscription and is not ingested without an explicit licence. DaData and self-hosted Photon/Pelias remain optional future adapters.

## Source Enrichment

- OSM / Overpass: place discovery and source tags.
- Geoapify: reverse geocoding and nearby place details.
- Wikidata / Wikimedia Commons: factual descriptions and photos.
- Official websites: JSON-LD, contacts, hours and images.
- City GO category rules: safe generic detail sections.

Existing non-empty verified values are not silently overwritten. Conflicts are written to `review_queue_items`.

## Data Quality

User surfaces reject:

- `node/way/relation` identifiers;
- every title ending with `OSM <number>`, including `Пляж OSM 1202021911`;
- placeholder and coordinate-only addresses;
- infrastructure categories in tourist routes;
- changed places before confirmation.

## Runtime

```env
GEOAPIFY_API_KEY=
PLACE_ADDRESS_GEOCODER_USER_AGENT=CityGoAddressBackfill/1.0
```

Without Geoapify the system still works, but Nominatim must be used slowly and cannot be treated as a high-volume scheduled provider.

## Verification

```bash
python -m pytest -q
npm --prefix frontend run lint
npm --prefix frontend run test:ci
npm --prefix frontend run build
```
