import type { ActiveRouteSession, RecommendationRouteResponse } from '../../api/recommendations/recommendationRoute.types'

const ROUTE_STORAGE_KEY = 'citygo:tma:activeRoute'
const SESSION_STORAGE_KEY = 'citygo:tma:activeRouteSession'

const isRoute = (value: unknown): value is RecommendationRouteResponse =>
  Boolean(value && typeof value === 'object' && Array.isArray((value as RecommendationRouteResponse).points))

const isSession = (value: unknown): value is ActiveRouteSession => {
  if (!value || typeof value !== 'object') return false
  const session = value as Partial<ActiveRouteSession>
  return typeof session.session_id === 'number' && typeof session.route_id === 'string' && typeof session.status === 'string'
}

export const restoreTmaRoute = (): RecommendationRouteResponse | null => {
  try {
    const raw = window.localStorage.getItem(ROUTE_STORAGE_KEY)
    if (!raw) return null
    const parsed: unknown = JSON.parse(raw)
    return isRoute(parsed) ? parsed : null
  } catch {
    return null
  }
}

export const saveTmaRoute = (route: RecommendationRouteResponse): void => {
  try {
    window.localStorage.setItem(ROUTE_STORAGE_KEY, JSON.stringify(route))
  } catch {
    // localStorage unavailable — route still works for this session, just not restored on reopen.
  }
}

export const clearTmaRoute = (): void => {
  try {
    window.localStorage.removeItem(ROUTE_STORAGE_KEY)
  } catch {
    // ignore
  }
  clearTmaRouteSession()
}

/** Restores the last known session state ONLY when it belongs to the given
 * route — a session for a different/stale route_id is stale local state
 * and must not be shown as if it were still authoritative. */
export const restoreTmaRouteSession = (routeId: string): ActiveRouteSession | null => {
  try {
    const raw = window.localStorage.getItem(SESSION_STORAGE_KEY)
    if (!raw) return null
    const parsed: unknown = JSON.parse(raw)
    if (!isSession(parsed) || parsed.route_id !== routeId) {
      clearTmaRouteSession()
      return null
    }
    return parsed
  } catch {
    clearTmaRouteSession()
    return null
  }
}

export const saveTmaRouteSession = (session: ActiveRouteSession): void => {
  try {
    window.localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session))
  } catch {
    // localStorage unavailable — session still works for this screen, just not restored on reopen.
  }
}

export const clearTmaRouteSession = (): void => {
  try {
    window.localStorage.removeItem(SESSION_STORAGE_KEY)
  } catch {
    // ignore
  }
}
