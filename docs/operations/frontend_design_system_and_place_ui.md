# Frontend Design System and Place UI

## Design tokens

City GO frontend design tokens live in `frontend/src/styles/design-system.css` and are imported once from `frontend/src/main.tsx`.

Core token groups:

- backgrounds: `--cg-bg-main`, `--cg-bg-card`, `--cg-bg-elevated`, `--cg-bg-muted`, `--cg-border-soft`;
- text: `--cg-text-main`, `--cg-text-muted`, `--cg-text-soft`, `--cg-text-disabled`;
- accents: `--cg-primary`, `--cg-primary-hover`, `--cg-primary-soft`, `--cg-route`, `--cg-open`, `--cg-warning`, `--cg-closed`, `--cg-rating`;
- radius: `--cg-radius-sm`, `--cg-radius-md`, `--cg-radius-lg`, `--cg-radius-xl`, `--cg-radius-pill`;
- shadows: `--cg-shadow-card`, `--cg-shadow-sheet`, `--cg-shadow-primary`.

Typography uses the system stack: `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif`. Shared text utilities include `cg-text-h1`, `cg-text-h2`, `cg-text-card-title`, `cg-text-body`, `cg-text-caption`, `cg-text-button`, plus `cg-clamp-1`, `cg-clamp-2`, `cg-clamp-3`.

## Base UI components

Base UI components live in `frontend/src/components/ui`.

- `Button`: variants `primary`, `secondary`, `ghost`, `danger`; sizes `sm`, `md`, `lg`; supports disabled and loading states.
- `Card`: variants `default`, `elevated`, `interactive`.
- `StatusBadge`: maps place status to Russian labels `Открыто`, `Закрыто`, `Уточнить`, `Скоро закроется`.
- `RatingBadge`: renders only when rating is a finite number; never renders `0`, dash, `null`, or `undefined` as fallback.
- `CategoryBadge`: renders localized category labels through `shared/place/categoryLabels`.
- `DistanceBadge`: renders only when distance is available.
- `Skeleton`: card, line, and circle placeholders on dark tokens.
- `EmptyState`: icon, title, description, CTA.
- `ErrorState`: icon, Russian error copy, retry CTA.
- `PlacePhoto`: `thumb`, `card`, `hero`; uses `object-fit: cover`, category fallback icon, and broken-image fallback.

## Place UI components

Place UI components live in `frontend/src/components/places`.

- `placeViewModel.ts`: normalizes place title, image, gallery, description, status, rating, reviews, distance, address, hours, tags, and detail block strings. It is the main guard against rendering `null`, `undefined`, raw backend category keys, broken images, or empty blocks.
- `PlaceCard`: list/search/recommendation card with photo, category, status, rating, distance, short description and click-through to detail.
- `PlaceList`: handles loading, loading more, success, empty, error, and no-city states. Uses 5 initial skeleton cards and 2 bottom skeleton cards.
- `PlaceDetailSheet`: detail view with hero photo/fallback, badges, collapsed description, optional sections and sticky safe-area-aware actions.
- `SearchBar` / `CitySearchBar`: debounced 300 ms search, inline loading, clear button and inline error slot.
- `FilterChips`: horizontal category chips with `Все` first and disabled zero-count categories.
- `FilterSheet`: bottom sheet filters with categories, only-open toggle, optional radius/rating controls, apply/reset actions.
- `PlaceMapPin`: canonical category pin contract for map integrations.
- `PlaceMapBottomCard`: canonical selected-place card for map integrations.

Supporting styles live in:

- `frontend/src/styles/place-ui.css`;
- `frontend/src/styles/place-ui-skeleton.css`.

## Migrated screens

Stage 2 migrated these user-facing place surfaces:

- `frontend/src/pages/places/PlacesListPage.tsx`: list, search, category chips, filter sheet, pagination sentinel.
- `frontend/src/pages/places/PlaceDetailPage.tsx`: loading/error states and `PlaceDetailSheet`.
- `frontend/src/pages/open-now/OpenNowResults.tsx`: shared `PlaceList`.
- `frontend/src/pages/nearby/NearbyResults.tsx`: shared `PlaceList`.

The existing backend endpoints and frontend API calls were not changed.

## Null and empty handling

The Place UI explicitly handles missing or empty values:

- no photo: `PlacePhoto` renders a dark category fallback and never passes `null` to `img src`;
- no rating: `RatingBadge` renders nothing;
- no review count: rating still renders without review count;
- no description: description block is omitted;
- no distance: distance badge is omitted;
- no address or placeholder address: address section is omitted in detail;
- no hours, phone, website, atmosphere, inside or best-for: the corresponding detail section/action is omitted.

## Stage 3 recommendation

Stage 3 should be Route UI Migration:

- migrate route cards to the same dark token system;
- show route points in visit order with clear step numbering;
- replace route tables/admin-like blocks in user UI with cards and timeline sections;
- add route state skeletons, empty states and error states;
- connect route detail actions to `Построить маршрут`, `Начать`, `Продолжить`, `Заменить точку` patterns;
- keep Telegram Mini App safe-area handling for sticky route controls.
