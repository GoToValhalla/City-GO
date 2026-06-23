# Frontend Design System and Product UI

## Design tokens

City GO frontend design tokens live in `frontend/src/styles/design-system.css` and are imported once from `frontend/src/main.tsx`.

Core token groups:

- backgrounds: `--cg-bg-main`, `--cg-bg-card`, `--cg-bg-elevated`, `--cg-bg-muted`, `--cg-border-soft`;
- text: `--cg-text-main`, `--cg-text-muted`, `--cg-text-soft`, `--cg-text-disabled`;
- accents: `--cg-primary`, `--cg-primary-hover`, `--cg-primary-soft`, `--cg-route`, `--cg-open`, `--cg-warning`, `--cg-closed`, `--cg-rating`;
- radius: `--cg-radius-sm`, `--cg-radius-md`, `--cg-radius-lg`, `--cg-radius-xl`, `--cg-radius-pill`;
- shadows: `--cg-shadow-card`, `--cg-shadow-sheet`, `--cg-shadow-primary`.

Typography uses the system stack: `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif`. Shared text utilities include `cg-text-h1`, `cg-text-h2`, `cg-text-card-title`, `cg-text-body`, `cg-text-caption`, `cg-text-button`, plus `cg-clamp-1`, `cg-clamp-2`, `cg-clamp-3`.

Legacy aliases such as `--ink`, `--muted`, `--line`, `--blue`, `--canvas`, and `--pearl` are mapped to the City GO tokens so older user-facing CSS does not fall back to the old light palette.

## Base UI components

Base UI components live in `frontend/src/components/ui`.

- `Button`: variants `primary`, `secondary`, `ghost`, `danger`; sizes `sm`, `md`, `lg`; supports disabled and loading states.
- `Card`: variants `default`, `elevated`, `interactive`.
- `Badge`: generic token-based badge for route and shared UI metadata.
- `StatusBadge`: maps place status to Russian labels `Открыто`, `Закрыто`, `Уточнить`, `Скоро закроется`.
- `RatingBadge`: renders only when rating is a finite number; never renders `0`, dash, `null`, or `undefined` as fallback.
- `CategoryBadge`: renders localized category labels through `shared/place/categoryLabels`.
- `DistanceBadge`: renders only when distance is available.
- `Skeleton`: card, line, and circle placeholders on dark tokens.
- `EmptyState`: icon, title, description, CTA.
- `ErrorState`: icon, Russian error copy, retry CTA.
- `PlacePhoto`: `thumb`, `card`, `hero`; uses `object-fit: cover`, category fallback icon, and broken-image fallback.
- `PageBreadcrumbs`, `SectionHeader`, `SurfaceCard`: token-based shared layout primitives.

## Place UI components

Place UI components live in `frontend/src/components/places`.

- `placeViewModel.ts`: normalizes place title, image, gallery, description, status, rating, reviews, distance, address, hours, tags, and detail block strings. It guards against rendering `null`, `undefined`, raw backend category keys, broken images, or empty blocks.
- `PlaceCard`: list/search/recommendation card with photo, category, status, rating, distance, short description and click-through to detail.
- `PlaceList`: handles loading, loading more, success, empty, error, and no-city states. Uses 5 initial skeleton cards and 2 bottom skeleton cards.
- `PlaceDetailSheet`: detail view with hero photo/fallback, badges, collapsed description, optional sections and sticky safe-area-aware actions.
- `SearchBar` / `CitySearchBar`: debounced 300 ms search, inline loading, clear button and inline error slot.
- `FilterChips`: horizontal category chips with `Все` first and disabled zero-count categories.
- `FilterSheet`: bottom sheet filters with categories, only-open toggle, optional radius/rating controls, apply/reset actions.
- `PlaceMapPin`: canonical category pin contract for map integrations.
- `PlaceMapBottomCard`: canonical selected-place card for map integrations.

Supporting product styles live in:

- `frontend/src/styles/place-ui.css`;
- `frontend/src/styles/place-ui-skeleton.css`;
- `frontend/src/styles/home.css`;
- `frontend/src/styles/actions.css`;
- `frontend/src/styles/cards.css`;
- `frontend/src/styles/places.css`;
- `frontend/src/styles/discovery.css`.

## Migrated user surfaces

The current product UI migration covers these user-facing surfaces:

- `frontend/src/pages/home/HomePage.tsx`: dark City GO home shell, hero, quick actions, stats and places preview.
- `frontend/src/pages/places/PlacesListPage.tsx`: list, search, category chips, filter sheet, pagination sentinel.
- `frontend/src/pages/places/PlaceDetailPage.tsx`: loading/error states and `PlaceDetailSheet`.
- `frontend/src/pages/open-now/OpenNowPage.tsx` and `OpenNowResults.tsx`: open-now surface with shared `PlaceList`.
- `frontend/src/pages/nearby/NearbyPage.tsx` and `NearbyResults.tsx`: nearby controls and shared `PlaceList`.
- `frontend/src/pages/routes/RoutesListPage.tsx`: route cards, filters, loading, empty and error states.
- `frontend/src/pages/routes/RouteDetailPage.tsx`: route summary and route navigation view in the dark token system.
- `frontend/src/pages/routes/GenerateRoutePage.tsx`: route builder shell, controls, result panels and route preview styled through City GO tokens.

Admin screens are intentionally not migrated into this product UI canon.

## Null and empty handling

The Place UI explicitly handles missing or empty values:

- no photo: `PlacePhoto` renders a dark category fallback and never passes `null` to `img src`;
- no rating: `RatingBadge` renders nothing;
- no review count: rating still renders without review count;
- no description: description block is omitted;
- no distance: distance badge is omitted;
- no address or placeholder address: address section is omitted in detail;
- no hours, phone, website, atmosphere, inside or best-for: the corresponding detail section/action is omitted.

## Remaining product work

Remaining user-facing work should continue in the same canon without stage framing:

- wire real map components to `PlaceMapPin` and `PlaceMapBottomCard` where a map implementation is available;
- add visual regression or Playwright coverage for 360, 390, 768, 1024, and 1440 px widths;
- review Telegram Mini App runtime safe-area behavior after deploy;
- remove any remaining legacy inline styles as pages are touched for feature work.
