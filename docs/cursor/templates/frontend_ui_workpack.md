# Workpack: Frontend UI (public)

## Goal
<Layout, empty state, PlaceCard, mobile overflow, report button>

## Read first
- `docs/cursor/TASK_SCOPES.md` → Public UI row
- `frontend/src/pages/<area>/`
- `frontend/src/shared/debug/`
- `frontend/src/components/places/PlaceCard.tsx`

## Do not touch
- Backend unless API contract wrong
- Admin panel unless task spans both

## Likely files
- `HomePage.tsx`, `OpenNowResults.tsx`, `NearbyResults.tsx`
- `frontend/src/styles/debug.css`

## Hard rules
- Normal mode: no raw technical noise
- Debug mode: diagnostics + «Сообщить о проблеме»
- Mobile-first; no horizontal overflow

## Tests
```bash
npm --prefix frontend test -- --run src/components/places/PlaceCard.test.tsx
npm --prefix frontend test -- --run src/shared/debug/
npm --prefix frontend run build
```

## Final response
Normal vs debug behavior · files · vitest · build · screenshots N/A unless requested
