import { ApiRequestError } from '../../api/recommendations/recommendationRoute.api'

/** The backend has no session TTL/expiry concept (models/route_session.py) —
 * "session not found" (a 4xx from POST /v1/user-routes/sessions/{id}/action)
 * is the only signal that a previously persisted session is no longer
 * valid, and is what "expired or invalid" means for a restored session. */
export const isSessionInvalidError = (error: unknown): boolean =>
  error instanceof ApiRequestError && error.status >= 400 && error.status < 500
