# City Go Web & Telegram UI Redesign

## Product Principle

City Go UI is a route decision surface, not a generic map clone. The first screen
must answer: what can I do now, how do I build a good route, and can I trust it?

## Web Structure

The web UI uses a quiet Apple-like shell from `DESIGN.md`: white/pearl canvas,
one action blue, restrained borders, 8px cards, and real place photos as the
primary visual signal. Letter spacing stays `0` to match project frontend rules.

Primary screens:

- Home: route-first hero, search, quick scenarios, clear photo carousel.
- Places: scannable cards with photo status, category, hours, duration, price,
  address, and direct detail/action links.
- Route builder: user-facing presets first, technical coordinates secondary.
- Route result: summary, warnings, time/distance/category insights, timeline,
  correction actions, and data notes.

## Telegram Structure

Telegram remains button-first and shallow:

- City selection before any route/place flow.
- Main menu has five actions max and two buttons per row.
- Route result is one readable message: summary, warnings, numbered points,
  correction hints.
- Callback data remains short; no JSON payloads.

## Safety

Fallback images are labelled honestly. Warnings are user-facing text, not raw
technical strings. Draft cities are never treated as fully available.

## Sites UI/UX Integration (2026-07-13)

The approved `CITY GO Design Preview` in ChatGPT Sites is a design source, not a
deployable branch of this repository. Sites uses an unrelated Vinext/Next-style
repository, while production City GO remains React/Vite + FastAPI. UI work is
ported into this codebase without replacing repository history, API contracts,
admin screens, diagnostics, or existing route correction flows.

Public web surfaces use a scoped light shell (`.app-screen`): pearl canvas,
white surfaces, dark primary actions, terracotta editorial accent, 12/24px
radii, a compact desktop header, and a three-item mobile bottom navigation.
Admin tokens remain unchanged.

The home screen is city-first:

- Header and hero open the same searchable city picker.
- Search matches city name, region, country, and slug.
- Every result is identified as `Название · Регион · Страна`; the slug remains
  the routing and persistence identity, so equal city names are unambiguous.
- The hero combines current-city facts with published place coordinates on the
  existing MapLibre surface.
- Quick actions preserve current catalog, nearby, open-now, and route URLs.

The random route editor exposes two explicit products over the existing
`POST /routes/random` endpoint:

- `random_places`: user-selected duration, `category_mode=none`, no categories.
- `random_mood`: seeded duration from 60/120/180/240 minutes and one to three
  loaded, city-supported categories with `category_mode=balanced`.

Both modes preserve the existing draft map, add/replace/remove actions, warning
handling, and route API response contract. No frontend-only demo fallback is
introduced.
