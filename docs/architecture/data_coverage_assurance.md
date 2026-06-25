# Data Coverage Assurance

City GO tracks expected important places separately from raw imports.

This page documents the first implementation layer:

- `models/known_missing_poi.py` stores expected places and reconciliation status.
- `data/config/known_missing_poi.json` stores repository seed data.
- `services/coverage_gap_service.py` syncs seeds and matches them to current places.
- `routers/admin_coverage_gaps.py` exposes admin endpoints.
- `frontend/src/pages/admin/AdminCoverageGapsPage.tsx` shows the admin dashboard.

The first regression city is Kutaisi, but the mechanism is global.
