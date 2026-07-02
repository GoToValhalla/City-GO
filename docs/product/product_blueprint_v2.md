# City GO — Product Blueprint v2

Date: 2026-07-02
Status: product source of truth
Jira: CITYGO-149

## 1. Product definition

City GO is a city discovery and route-building product. It helps a person quickly understand what to see, where to walk, what to skip, and how to build a realistic route without manual research.

City GO is not only a route builder. It includes:

1. destination launch pipeline;
2. place ingestion and enrichment;
3. moderation and publication;
4. search and recommendation;
5. route planning;
6. Telegram Mini App and web client;
7. admin platform;
8. observability and quality control.

## 2. Product goals

Primary goals:

- give a user a usable route in less than one minute;
- prevent garbage places from appearing in public routes;
- scale destination launch without manual coding per city;
- keep city/place quality visible to admin;
- make route output explainable and editable;
- allow gradual migration to projections and services without rewriting everything.

Non-goals for the near term:

- full travel marketplace;
- booking engine;
- social network;
- full navigation engine;
- microservice split before product proof.

## 3. Target audience

### Tourist with no plan

Needs fast route and minimal choices.

Main mode: Auto / Quick Build.

### Tourist with preferences

Knows interests: architecture, food, parks, history, evening walk, family route.

Main mode: Category Builder.

### Power user

Wants to control order, duration, places, replacements.

Main mode: Manual Build / Slot Builder.

### Admin / city operator

Launches city, monitors data quality, reviews places, approves publication, controls imports and enrichment.

### Future partner

Can provide data, photos, routes, sponsor locations or city recommendations. Not a day-one role.

## 4. Core user promises

The product must answer:

- what is worth seeing here;
- what is open and realistic now;
- how much time it will take;
- why these places were selected;
- what can be replaced;
- how to avoid pharmacies, bus stops, banks and other non-tourist noise;
- how to continue or rebuild the route.

## 5. Route modes

### Mode 1 — Auto / Quick Build

Input:

- city;
- optional start point;
- available time;
- optional interests.

Output:

- route with 3+ meaningful points when enough data exists;
- route summary;
- warnings;
- map/list/timeline.

Rules:

- no service garbage;
- no impossible time budget;
- no hidden/unpublished places;
- no route from raw import tables;
- route reads routing projections.

### Mode 2 — Category Builder

Input:

- city;
- categories/interests;
- route duration;
- start point.

Output:

- balanced route across chosen categories.

Rules:

- category caps;
- no three food-only points unless route type is food route;
- quality score influences ranking;
- route should explain category match.

### Mode 3 — Manual Build

Input:

- user-selected places;
- optional order;
- duration constraints.

Output:

- optimized route/order;
- warnings about distance, hours, quality.

Rules:

- user intent has priority;
- unavailable/closed/hidden places are blocked or warned;
- route can be saved.

### Mode 4 — Slot Builder

Input:

- slots such as breakfast, museum, park, coffee, sunset;
- duration;
- geography constraints.

Output:

- route filled by best candidates per slot.

Rules:

- slot candidates come from projections;
- fallback allowed if slot is impossible;
- user sees missing slot explanation.

## 6. Destination lifecycle

```text
idea -> prospecting -> importing -> enrichment -> review_required -> publishable -> published -> maintenance -> hidden -> archived
```

Rules:

- destination cannot become public only because import finished;
- quality gate is required before publication;
- hidden destination hides public read models but keeps internal data;
- maintenance allows reimport/enrichment without unpublishing.

## 7. Place lifecycle

```text
raw_observed -> candidate -> enriched -> review_required -> approved -> published -> hidden -> archived
```

Additional states:

- duplicate_suspected;
- conflict_open;
- ai_candidate_pending;
- missing_critical_data;
- quality_blocked.

Rules:

- AI creates candidates, not public facts;
- import creates observations and candidates, not public publication;
- publication creates snapshots;
- public clients read snapshots/projections.

## 8. Route lifecycle

```text
requested -> candidates_loaded -> route_built -> partial -> failed -> preview -> active -> paused -> completed -> abandoned -> rebuilt
```

Route statuses:

- succeeded;
- partial;
- empty;
- failed.

Warnings:

- not enough places;
- long initial transfer;
- stale projection;
- low media coverage;
- missing hours;
- time budget too tight;
- candidate quality low.

## 9. Admin roles

### Viewer

Can inspect dashboards and entities.

### Reviewer

Can approve/reject candidates and manual queue items.

### Publisher

Can publish, hide and rollback places/destinations.

### Operator

Can run imports, enrichment and projection rebuild jobs.

### Admin

Can manage settings, roles, kill switches and feature flags.

Rules:

- destructive actions require reason;
- bulk apply requires dry run;
- publication actions require event and audit;
- rollback requires snapshot version.

## 10. Recommendation rules

Recommendation is a ranking layer over published projections.

Inputs:

- city;
- route mode;
- interests;
- time budget;
- start point;
- category diversity;
- place quality;
- distance;
- opening hours;
- media presence;
- prior user actions.

Hard exclusions:

- unpublished;
- hidden;
- inactive;
- no coordinates;
- service-only garbage;
- route-ineligible;
- blocked category;
- stale critical facts when required.

Soft penalties:

- missing photo;
- missing hours;
- low confidence;
- duplicate suspicion;
- long walking segment;
- poor category diversity.

## 11. AI rules

AI tasks:

- draft descriptions;
- category suggestions;
- fact extraction;
- conflict explanation;
- route explanation;
- review assistance.

AI cannot:

- directly publish;
- directly approve facts;
- directly edit public snapshots;
- bypass review gates;
- overwrite manual decisions.

AI must:

- use prompt versions;
- store task run metadata;
- produce candidates;
- pass regression gates before prompt rollout;
- respect cost budget policy.

## 12. Publication rules

Publication is the only path to public read models.

Publication requires:

- approved facts;
- quality gate pass;
- actor;
- reason;
- event;
- snapshot version.

Publication creates:

- PlaceSnapshot / PublishedPlaceSnapshot;
- search projection;
- routing projection.

Rollback requires:

- target snapshot version;
- actor;
- reason;
- event;
- audit log.

## 13. Quality rules

City quality:

- enough places;
- category diversity;
- photo coverage;
- address coverage;
- description coverage;
- hours coverage;
- route eligibility;
- duplicate rate;
- spam/service noise rate.

Place quality:

- title;
- category;
- coordinates;
- description;
- photo;
- address;
- hours;
- verification confidence;
- tourist eligibility;
- route eligibility.

Quality is not publication state. It can block publication, but it must not silently unpublish product state.

## 14. Product invariants

- Import cannot unpublish.
- AI cannot publish.
- Quality cannot silently change publication state.
- Public clients do not read raw observations.
- Search and routing read projections.
- Bulk destructive admin action requires dry run.
- Rollback requires snapshot version.
- New feature must declare: client/API -> bounded context -> source of truth/projection -> event/audit -> tests.

## 15. Open decisions

- first production city after architecture cleanup;
- Telegram Mini App priority vs web priority;
- route engine v2 algorithm depth;
- photo sourcing strategy;
- paid features timing;
- partner data ingestion policy.
