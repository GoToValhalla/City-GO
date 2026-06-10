# 03 — UI/UX Redesign Audit

> Product UX due diligence of the City Go web frontend (`frontend/src`, React 19 + Vite 8 + react-router 7, global CSS). No UI implemented. No mockups. Concrete files only.
> Classification: REAL DEFECT · TECHNICAL DEBT · PARTIALLY IMPLEMENTED · FUTURE ROADMAP · INTENTIONALLY DEFERRED · REQUIRES VERIFICATION

---

## 1. Executive Summary

City Go web is a compact, route-first SPA with a genuinely strong route generator (`pages/routes/GenerateRoutePage.tsx` + 13 `widgets/recommendation-route/*`). But as a **tourist-facing product it is not launch-ready** for three structural reasons:

1. **No map.** No Leaflet/Google/2GIS/Yandex anywhere in `package.json` or UI. Places and routes are text lists with text coordinates. Every competitor (Google Maps, 2GIS, Yandex, Tripadvisor) is map-first. For a *city walking* product this is the single biggest gap. → PARTIALLY IMPLEMENTED / launch blocker for product-market fit.
2. **Inconsistent city context.** City lives in `localStorage` (`shared/city/currentCity.ts`) but `RoutesListPage` hardcodes `getRoutesByCity('zelenogradsk')` and `NearbyPage` defaults to Zelenogradsk center — they ignore the selected city. → REAL DEFECT.
3. **Missing states.** Several result grids (`PlacesListPage`, `NearbyResults`, `OpenNowResults`, `HomePage PlacesSection`) lack loading skeletons and/or empty states; `RouteDetailPage` has no empty-points message; `index.html` ships `lang="en"` and title "frontend". → TECHNICAL DEBT / polish blockers.

It is **not a Telegram WebApp** (no Telegram WebApp SDK) and has **no bottom navigation** (desktop-first header nav), despite the product's primary channel being mobile/Telegram. → TECHNICAL DEBT.

---

## 2. Product UX Evaluation (by persona)

| Persona | Experience today | Verdict |
|---|---|---|
| First-time tourist | Lands on route-first home (`HomePage`), can build a route in ~2 clicks, but cannot see anything on a map; address text only | Mixed — strong intent, weak spatial orientation |
| Returning tourist | No saved session/route history surfaced in nav (`/routes` list is hidden from `AppHeader`); city persists in localStorage | Weak — returning value not surfaced |
| User already in the city | Nearby exists (`/nearby`) but defaults to Zelenogradsk center, not device GPS by default; no "near me now" one-tap | Weak |
| Mobile user | Responsive CSS (breakpoints 780/430px) but no bottom tab bar, horizontal-scroll nav, no map | Mixed |
| Telegram user | Web is not embedded as Telegram WebApp; bot is a separate channel (see File 04) | Gap |
| Competitor-savvy user | Expects map, pins, "open now near me", reviews/ratings — none present | Below expectation |

---

## 3. Screen-by-Screen Audit

### Home — `pages/home/HomePage.tsx`
1. Goal: pick a scenario / start a route. 2. JTBD: "show me what to do here now." 3. Primary action: build route / quick action. 4. Secondary: search, browse places. 5. Time-to-value: fast (route in ~2 clicks). 6. First-time: clear hero but static "2 часа в городе" preview (not live). 7. Returning: no continuation of last session. 8. Mobile: column layout OK. 9. Navigation cost: low. 10. Cognitive load: moderate. 11. Missing states: **no empty state** when city has 0 places (renders empty grid). 12. Loading: weak (meta text "Загрузка...", no skeleton). 13. Empty: missing. 14. Error: present (`state-panel-error`). 15. A11y: `LocationCarousel` is a `return null` stub (`widgets/home/LocationCarousel.tsx`) — DESIGN.md promises a photo carousel. 16. Conversion risk: static preview undersells. 17. Visual: OK (Apple-like tokens match DESIGN.md). 18. Redesign: live preview from real route API; add map teaser; real photo carousel. → PARTIALLY IMPLEMENTED.

### Places List — `pages/places/PlacesListPage.tsx`
Primary: browse/filter places. Loading: **no grid skeleton/spinner**. Empty: present ("ничего не найдено"). Error: present. **Pagination promised in copy but no button** ("Остальные места доступны через следующую подгрузку"). Search is client-side filter of already-loaded places, not server search (`/places/search` exists but unused here). Redesign: wire server search + real pagination/infinite scroll; add list/map toggle. → TECHNICAL DEBT (pagination), REAL DEFECT (dead "load more" copy).

### Place Detail — `pages/places/PlaceDetailPage.tsx`
Shows image (honesty badge), facts, "Собрать маршрут" link. **Admin moderation buttons inline on a public page** (POST `/admin/place-images/*`, `/admin/place-verifications/*`, no auth header) → REAL DEFECT (will 401, role confusion). No 404 empty state (only catch→error). Redesign: remove admin actions; add map mini, hours, "build route from here" prefill. 

### Routes Generate — `pages/routes/GenerateRoutePage.tsx`
Strongest screen. Components: `RouteHeroPreview`, `RouteRequestForm`, `RouteTimeControls`, `RouteResultPanel` (`RoutePointList`, `RouteWarnings`, `RouteDebugTrace`, `RouteCandidateOptions`). States: loading/error/empty(no_route) all handled. Issue: **`RouteDebugTrace` (developer-facing) is shown on a user screen**. Redesign: hide debug behind a flag; render route on a map. → TECHNICAL DEBT.

### Routes List — `pages/routes/RoutesListPage.tsx`
**City hardcoded** `getRoutesByCity('zelenogradsk')` (ignores selector) → REAL DEFECT. **Not linked in `AppHeader` nav** (URL-only) → TECHNICAL DEBT. States present.

### Route Detail — `pages/routes/RouteDetailPage.tsx`
Loading/error present; **no empty-points message**. Shows title + place links only — no photos, addresses, or map. Redesign: rich stops with images + map polyline. → PARTIALLY IMPLEMENTED.

### Nearby — `pages/nearby/NearbyPage.tsx`
Defaults to Zelenogradsk center, **not device GPS / selected city** → REAL DEFECT. `NearbyResults` has **no loading UI** (empty grid while fetching). Empty via `EmptyState`. Redesign: request geolocation, map with radius, sync to city. 

### Open Now — `pages/open-now/OpenNowPage.tsx`
Uses selected city. `OpenNowResults` **no loading state**. Empty via `EmptyState`. Redesign: add loading skeleton, "open near me" combining nearby + open-now.

### Admin Photo Review — `pages/admin/PhotoReviewPage.tsx`
Covered in File 02 (no shell, no token). 

---

## 4. Main User Flows

| Flow | Steps today | Friction | Class |
|---|---|---|---|
| First app launch | Land home → pick city (header `<select>`) | City selection buried in a `<select>`; `index.html` lang/title wrong | TECHNICAL DEBT |
| Build first route | Nav "Маршрут" → fill form → submit | Long form; no map result; debug trace visible | PARTIALLY IMPLEMENTED |
| Find a place | Home search (client filter) or "Места" | No server search; quick-action "Кофе" → `/places` without category filter | REAL DEFECT (filter not applied) |
| Open place details | Card → detail | Admin buttons on public page | REAL DEFECT |
| Find nearby | Nav "Рядом" | Wrong default location; no auto-GPS; no map | REAL DEFECT |
| Find open now | Nav "Открыто" | No loading state | TECHNICAL DEBT |
| Review generated route | On generate page result panel | No map; debug trace exposed | PARTIALLY IMPLEMENTED |
| Understand route warnings | `RouteWarnings` renders backend warnings | Good (honest) | OK |
| Start/follow route | Not supported | — | FUTURE ROADMAP |
| Return after session | No surfaced history/continuation | Returning value lost | TECHNICAL DEBT |

---

## 5. Mobile-First Audit

- Responsive via `styles/responsive.css` (780/430px). No bottom tab bar; nav is horizontal-scroll on mobile. → TECHNICAL DEBT.
- No Telegram WebApp SDK; web is not embedded in the bot. → TECHNICAL DEBT.
- Touch targets: header `<select>` for city is not a mobile-friendly city picker. → TECHNICAL DEBT.
- No map = no pinch/zoom spatial UX expected on mobile travel apps. → PARTIALLY IMPLEMENTED.

---

## 6. Visual Design Audit

- Tokens match `DESIGN.md` (Apple-like, Action Blue `#0066cc`) — `index.css`. Good.
- Breadcrumbs mix EN/RU ("Home", "Routes" vs Russian). → TECHNICAL DEBT.
- `index.html`: `lang="en"`, title "frontend". → REAL DEFECT (SEO/a11y/branding).
- `LocationCarousel` stub (`return null`) vs DESIGN promise. → PARTIALLY IMPLEMENTED.

---

## 7. Information Architecture

- Single shell: `components/ui/AppHeader.tsx`. Nav: Главная, Места, Открыто, Рядом, Маршрут. **`/routes` (saved routes) is not in nav.** → TECHNICAL DEBT.
- Dead code: `pages/routes/RoutesPage.tsx` (not routed), `api/itinerary/itinerary.api.ts` (unimported). → TECHNICAL DEBT.
- `WalkRoutePage` is a legacy redirect. → INTENTIONALLY DEFERRED.

---

## 8. Competitor Comparison

| Capability | City Go | Google Maps | 2GIS | Yandex Maps | Tripadvisor |
|---|---|---|---|---|---|
| Map-first browse | ❌ | ✅ | ✅ | ✅ | ✅ |
| Pins / clustering | ❌ | ✅ | ✅ | ✅ | ✅ |
| "Near me now" one-tap | ❌ (wrong default) | ✅ | ✅ | ✅ | ✅ |
| Open-now filter | ✅ (`/open-now`) | ✅ | ✅ | ✅ | partial |
| Route/itinerary builder | ✅ (strong) | ✅ (directions) | ✅ | ✅ | ✅ (trips) |
| Ratings/reviews | ❌ | ✅ | ✅ | ✅ | ✅ |
| Photos with provenance | ✅ (honesty badge) | ✅ | ✅ | ✅ | ✅ |
| Curated walking routes | ✅ (`/routes`) | ❌ | partial | partial | ✅ |

**City Go's differentiator** is the curated, time-budgeted walking route generator. Its **table-stakes gap** is the map + "near me". Redesign should double down on routes while adding a minimal map layer.

---

## 9. Recommended Redesign Direction

1. **Add a map layer** (Leaflet + OSM tiles, free) for: nearby, route result polyline, place detail mini-map. Lowest-cost path to competitive parity; reuses existing lat/lng.
2. **Fix city context**: single `useCurrentCity()` source feeding Routes/Nearby/Open-now; remove hardcoded `zelenogradsk`.
3. **Mobile shell**: bottom tab bar (Home, Places, Nearby, Routes), mobile city picker.
4. **State completeness**: shared `LoadingSkeleton`/`EmptyState`/`ErrorPanel` applied to every result grid.
5. **Route-first polish**: live home preview, hide `RouteDebugTrace` behind dev flag, map render of route.
6. **Server search + pagination** on places.
7. **Remove admin from public pages**; fix `index.html` lang/title; finish `LocationCarousel`.

---

## 10. UI/UX Backlog

**P0 (launch blockers)**
- UX-1: Fix city context (Routes/Nearby ignore selector). Files: `pages/routes/RoutesListPage.tsx`, `pages/nearby/NearbyPage.tsx`, `shared/city/currentCity.ts`. Size S.
- UX-2: Remove admin moderation buttons from public `PlaceDetailPage.tsx`. Size S.
- UX-3: Add loading + empty states to `NearbyResults`, `OpenNowResults`, `PlacesListPage`, home `PlacesSection`. Size M.
- UX-4: Fix `index.html` `lang="ru"` + real title; localize breadcrumbs. Size S.

**P1**
- UX-5: Minimal map layer (Leaflet) for nearby + route result. Size L.
- UX-6: Real server search + pagination on places (use `/places/search`). Size M.
- UX-7: Nearby uses device geolocation by default. Size M.
- UX-8: Hide `RouteDebugTrace` behind dev flag. Size S.
- UX-9: Add `/routes` (saved routes) to nav. Size S.

**P2**
- UX-10: Mobile bottom tab bar + mobile city picker. Size M.
- UX-11: Finish `LocationCarousel` per DESIGN.md. Size M.
- UX-12: Place detail map mini + "build route from here" prefill. Size M.
- UX-13: Remove dead code (`RoutesPage.tsx`, `itinerary.api.ts`). Size S.

**P3**
- UX-14: Ratings/reviews surface. FUTURE ROADMAP.
- UX-15: Telegram WebApp embedding of web. Size L. (See File 04.)

---

## 11. First Implementation Prompt

```
Implement UI P0 batch from docs/audits/03_ui_ux_redesign_audit.md (city context + public states + meta).

Scope (frontend only):
- UX-1: introduce a single useCurrentCity() consumed by RoutesListPage and NearbyPage; remove hardcoded 'zelenogradsk'
  and Zelenogradsk-center default; fall back to selected city center only.
- UX-2: remove admin moderation buttons from pages/places/PlaceDetailPage.tsx (public page must not call /admin/*).
- UX-3: add shared LoadingSkeleton + EmptyState to NearbyResults, OpenNowResults, PlacesListPage, home PlacesSection.
- UX-4: index.html lang="ru" + real <title>; localize PageBreadcrumbs labels.

Constraints: do not add a map yet (separate P1), do not touch backend, do not touch telegram, do not change route engine.

Tests (Vitest, suffix _new): RoutesListPage requests selected city; NearbyResults shows loading then empty; PlaceDetailPage renders no admin buttons.
Docs: note changes in docs/architecture/web_bot_ui_redesign.md.

Analyze first, then implement. Report changed files, tests run, residual risks in one block.
```
