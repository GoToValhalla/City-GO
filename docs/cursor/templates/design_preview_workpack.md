# Workpack: Design preview / UX polish

## Goal
<Visual tweak, empty state, copy — no backend change>

## Read first
- `DESIGN.md` (relevant section only)
- Target page/component under `frontend/src/`

## Do not touch
- Business logic, API contracts, migrations
- Broad admin redesign

## Likely files
- Page `.tsx` + `.css`
- Component tests

## Hard rules
- Mobile-first
- Preserve debug/report actions
- Russian copy for user-facing strings

## Tests
```bash
npm --prefix frontend test -- --run <Component>.test.tsx
npm --prefix frontend run build
```

## Final response
UX change summary · files · tests · what was not visually verified (Playwright)
