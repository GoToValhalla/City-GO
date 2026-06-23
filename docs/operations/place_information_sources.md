# Place Information Sources

City GO needs full, reliable place profiles without inventing facts. The target model is source-first: collect observations, store source and freshness, calculate field confidence, then publish only fields that pass quality rules.

## Source options

1. OpenStreetMap / Overpass

Use as the baseline for coordinates, categories, addresses, phone, website and opening hours. Coverage is free and broad, but quality varies by city and field. OSM should be treated as a strong starting layer, not as the only source of truth.

2. Wikidata, Wikimedia Commons, Wikipedia and Wikivoyage

Use for landmarks, museums, monuments, historical objects, photos, short encyclopedic descriptions, official links and heritage metadata. This is strong for cultural places and weak for ordinary cafes, shops and local services.

3. Official websites and public pages

Use official site pages, Open Graph metadata, schema.org, contact pages and public menus/pages for address, description, photos, phone, working hours and website. This should have higher confidence than generic aggregators when the source is clearly official.

4. Local tourism portals and open data

Use city/regional tourism portals, museum directories, event calendars and public datasets for curated descriptions, collections, routes and seasonal notes. These are useful for travel quality and not only raw POI data.

5. Commercial place APIs

Yandex Maps, 2GIS and Google Places can provide richer business data: current hours, ratings, photos, reviews and phone numbers. They require separate legal/product decisions because storage and display of photos, reviews and ratings can be restricted by API terms. Prefer storing provider ids and source metadata unless the license explicitly allows persistence.

6. Admin verification and user signals

Use admin review queue, manual verification, user reports, favorites, route usage and skipped places to improve public fields and recommendations. Human review is required for low-confidence hours, addresses, categories and photos.

7. AI enrichment layer

AI may summarize and classify only from collected source observations. It must not hallucinate place facts. Every generated description should keep links to source observations and confidence metadata.

## Recommended data flow

1. Ingest raw observations into a `place_source_observations`-style table: provider, source URL/id, field name, raw value, fetched timestamp and license/usage notes.
2. Normalize observations into candidate fields: title, category, address, coordinates, phone, website, hours, photos, descriptions, tags and seasonal notes.
3. Score each field in `place_field_confidence`: confidence, freshness, source priority and conflict state.
4. Send conflicts and low-confidence fields to admin review.
5. Publish only approved or high-confidence fields to public UI, bot and Mini App.

## Fields City GO should target per place

- title and localized category;
- coordinates and address;
- short description and detail sections;
- photos with source and match status;
- opening hours and reliability status;
- phone and website;
- rating/review count only from sources where usage is allowed;
- tags: atmosphere, inside, audience, budget, seasonality, dog-friendly, family-friendly, route eligibility;
- source freshness and confidence.

## Product rule

Public UI must never show `null`, raw backend keys or invented values. If a field is missing, the block is hidden or shown as `Уточнить` only where uncertainty is useful to the user.
