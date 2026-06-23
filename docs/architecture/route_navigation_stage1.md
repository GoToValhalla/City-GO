# Route Navigation Stage 1

Stage 1 adds a frontend-only route player for public route detail pages.

## Scope

- Show route points on a deterministic SVG schematic.
- Connect valid points with straight segments.
- Persist navigation state in `localStorage` by route id.
- Let users manually start, mark points visited, move to the next point, complete, and reset.

## Data Contract

The public route detail response exposes read-only point fields required by the player:

- coordinates: `lat`, `lng`;
- quality flags: `is_published`, `is_route_eligible`, `publication_status`, `is_active`, `status`;
- display fields: `category`, `address`.

No backend route session or tracking table is created in Stage 1.

## Quality Gate

The frontend filters navigation points before rendering markers:

- missing place id;
- missing coordinates;
- hidden/unpublished/inactive places;
- `is_route_eligible=false`;
- service categories such as pharmacy, bank, police, parking, fuel.

If fewer than two valid points remain, route start is disabled and the UI explains the blockers.

## Stage 2 Candidates

- Replace SVG renderer internals with MapLibre.
- Add optional GPS current position.
- Add OSRM/polyline walking geometry.
- Persist user route sessions on backend.
