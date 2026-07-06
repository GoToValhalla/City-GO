---
name: backend-endpoint
description: Add or modify a City GO FastAPI endpoint. Use for new routers, admin/public API changes, or service contract updates.
---

# Backend endpoint

## When to use

New or changed API route under `routers/`, admin or public.

## Inputs

- Path, method, auth role
- Request/response shape
- Affected domain (places, routes, admin, destinations, etc.)

## Steps

1. Find similar router + service + schema + tests (e.g. `routers/places.py`, `tests/test_places_router_*.py`).
2. Define Pydantic schema in `schemas/`; implement logic in `services/`; thin handler in `routers/`.
3. Auth: `core/admin_auth.py` for `/admin/*`; never trust client identity fields.
4. Add/update pytest: success, 401/403, validation errors, contract fields.
5. Run: `.venv/bin/python -m pytest tests/<relevant> -q --no-cov`

## Validation

- Contract matches existing API style
- Tests cover auth and main behavior

## Response format

- **Endpoint** (method + path)
- **Changed files**
- **Tests run**
- **Risks** (breaking changes, migration needed, flags)
