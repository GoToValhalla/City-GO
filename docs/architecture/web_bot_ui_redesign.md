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
