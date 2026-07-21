import { ApiRequestError } from '../../api/recommendations/recommendationRoute.api'

/** The backend has no session TTL/expiry concept (models/route_session.py) —
 * "session not found" (a 4xx from POST /v1/user-routes/sessions/{id}/action)
 * is the only signal that a previously persisted session is no longer
 * valid, and is what "expired or invalid" means for a restored session. */
export const isSessionInvalidError = (error: unknown): boolean =>
  error instanceof ApiRequestError && error.status >= 400 && error.status < 500

/** A stale-revision/route-mismatch conflict (HTTP 409, code
 * "route_state_conflict" -- see routers/user_routes.py::_route_state_http_error
 * and _ensure_route_id_matches) means the mutation was correctly rejected
 * because the client's view of the route is out of date, not that the
 * request itself failed generically. Collapsing this into the generic
 * "не удалось обновить" message hides that a reload/resync is required. */
export const isRouteStateConflictError = (error: unknown): boolean =>
  error instanceof ApiRequestError &&
  error.status === 409 &&
  typeof error.responseBody === 'object' &&
  error.responseBody !== null &&
  (error.responseBody as { detail?: { code?: string } }).detail?.code === 'route_state_conflict'
