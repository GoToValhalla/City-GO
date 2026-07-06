# Workpack: Route bug

## Goal
<Empty route, 1-point route, wrong POI types, missing warnings>

## Read first
- `docs/cursor/TASK_SCOPES.md` → Route row
- `services/candidate_retrieval_service.py`
- `services/route_builder_v2_service.py`
- `frontend/src/widgets/recommendation-route/RouteResultPanel.tsx`

## Do not touch
- Import pipeline unless data quality is root cause
- Normal UI debug noise (keep debug mode separate)

## Likely files
- `services/route_eligibility.py`
- `routers/user_routes.py`
- `RouteResultPanel.test.tsx`

## Hard rules
- No pharmacies/banks/stops in tourist routes by default
- 1-point route ≠ full success in normal UI
- Warnings/debug_trace preserved in debug mode

## Tests
```bash
.venv/bin/python -m pytest tests -q -k "route" --no-cov
npm --prefix frontend test -- --run src/widgets/recommendation-route/
```

## Final response
Pipeline stage where places lost · warning codes · files · tests · manual ?debug=1 check
