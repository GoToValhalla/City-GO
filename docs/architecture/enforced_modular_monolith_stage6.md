# City GO Stage 6 — Enforced Modular Monolith

Date: 2026-07-22

Status: implemented
Jira: CITYGO-380 through CITYGO-388

## Executable source of truth

`architecture/stage6_manifest.json` is the only Stage 6 ownership manifest. It
declares every one of the 139 SQLAlchemy tables exactly once, including owner,
table type, one authorized writer and readers. `architecture/manifest.py`
loads the manifest, while architecture tests compare it with real metadata.
The older extraction registry remains historical product data; it is not an
architecture authority and cannot override the version-controlled manifest.

## Dependency direction

- Search and Routing are independent peers. Neither may import the other.
- Route Sessions may consume Routing artifacts. Routing may not consume Route
  Sessions.
- Publication is the only publication-state writer.
- Projection Infrastructure is the only projection writer.
- Destination owns destination membership. Non-owners query it through
  `services.stage6_contracts.destination`.
- Destination may submit scalar catalog-reference changes through
  `services.stage6_contracts.catalog`; Catalog has no declared dependency on
  Destination. Read adapters that combine both domains are outside the Catalog
  write boundary.

All communication remains typed and synchronous inside the existing process.
No broker, outbox, dual-write path, service extraction or new persistence was
introduced.

## Application boundaries

The public synchronous contracts live in `services/stage6_contracts/`:

- `catalog.py`: ordinary Place mutation and Destination scalar reference state;
- `publication.py`: canonical publication transition;
- `destination.py`: membership commands and identity queries;
- `media.py`: immutable moderation result;
- `quality.py`: immutable quality evaluation;
- `routing.py`: immutable public route artifact;
- `projection.py`: typed Stage 5 rebuild dispatch;
- `review_quality.py`: explicit review decisions and evidence-only quality findings.

Transaction ownership is explicit. Contracts either do not commit or delegate
to an existing service whose transaction behavior is already part of the API.
Canonical publication and verification rules were not duplicated.

## Admin isolation

The seven Stage 6 admin/feedback routers contain authentication, request
validation, HTTP error mapping and service invocation only. Their ORM queries,
mutations, locks, commits and rollbacks live in application services. The CI
guard checks those exact routers for model imports and transaction calls.

## Review and quality lifecycles

The overlapping names represent distinct evidence and are intentionally not
merged:

| Table | Owner | Lifecycle |
|---|---|---|
| `reviews` | Identity | user-authored product review |
| `review_queue_items` | Import | operational import moderation queue |
| `review_items` | Import | enrichment moderation evidence |
| `place_change_reviews` | Publication | decision over a canonical place change |
| `data_quality_issues` | Quality | data-quality detector output |
| `quality_issues` | Quality | taxonomy/rule finding |

Quality findings are evidence and cannot carry a publication target state.
Publication consumes an explicit typed review decision and translates it
through the canonical publication writer. Historical rows and lifecycle
semantics remain unchanged, so Stage 6 requires no data migration.

## Destination compatibility references

`places.primary_destination_id` remains a denormalized scalar on the
Catalog-owned Place. Destination updates it only through the Catalog contract.
`destinations.legacy_city_id` remains a Destination-owned, read-only bridge to
the stable City identifier for Stage 0–5 compatibility. It is not shared table
ownership and must not become a reverse Catalog repository dependency.

## Enforcement and rollback

`tests/test_stage6_architecture_manifest.py`,
`tests/test_stage6_dependency_guards.py` and
`tests/test_stage6_application_contracts.py` run as a dedicated CI step before
the full backend suite. A new context, table, writer, dependency or isolated
router violation therefore fails CI with a deterministic file and line.

Stage 6 changes module boundaries only. Rollback is a normal deployment rollback
to the prior image; there is no database downgrade, data copy, compatibility
write or projection rebuild involved. Stage 5 projection ON/OFF contracts and
schemas are unchanged.
