# City GO — Route Builder v2

Date: 2026-07-02
Status: implementation contract
Roadmap: Phase 4 — Route Builder v2
Jira: CITYGO-156
Existing epic: CITYGO-5

## Goal

Make route creation explicit and testable across four product modes without introducing a second route engine.

The existing `services/route_engine.py` strategy layer remains the executor foundation. Route Builder v2 adds a deterministic request/plan contract above it.

## Modes

### Quick Build

Low-friction route creation. The user provides minimal parameters and receives an instant route plan.

Rules:

- aliases `auto`, `instant` and `quick_build` normalize to `quick`;
- executor mode remains `instant`;
- extra category/manual data is ignored with explicit warnings;
- expected minimum points: 3.

### Category Builder

User chooses categories/formats and the system builds around them.

Rules:

- at least one category is required;
- duplicate categories are removed while preserving order;
- expected minimum points is derived from selected categories.

### Manual Builder

User chooses route points directly.

Rules:

- at least two selected places are required;
- selected place ids preserve user order;
- duplicate place ids are removed;
- expected minimum and maximum points equal selected point count.

### Slot Builder

User defines route structure and the system fills slots.

Rules:

- at least one slot is required;
- each slot requires type or category;
- slot min/max bounds must be valid;
- total max points cannot exceed route max;
- expected point bounds are computed from slot bounds.

## Service contract

Implemented in `services/route_builder_v2_service.py`.

Public helpers:

- `RouteBuilderV2Request`;
- `RouteBuilderV2Plan`;
- `normalize_route_builder_request()`;
- `normalize_mode()`;
- `assert_route_builder_v2_mode_supported()`;
- `build_route_builder_v2_plan()`.

## Invariants

- Route Builder v2 is a contract layer, not a second route engine.
- All modes normalize into a deterministic plan.
- Invalid mode-specific input is rejected before execution.
- The executor remains compatible with existing instant route strategy.
- Manual ordering is user-owned and preserved.
- Slot bounds are explicit and safe.

## Test coverage

Covered in `tests/test_route_builder_v2_service.py`:

- four supported modes;
- alias normalization;
- city requirement;
- positive duration requirement;
- category unique-order normalization;
- quick build warnings;
- category builder required categories;
- manual builder point order and duplicate removal;
- manual builder minimum point count;
- slot builder slot normalization;
- slot builder point bounds;
- invalid slot and max-points rejection.

## Exit criteria

- Quick Build contract exists;
- Category Builder contract exists;
- Manual Builder contract exists;
- Slot Builder contract exists;
- tests exist;
- repo and Confluence docs exist;
- CI is green.
