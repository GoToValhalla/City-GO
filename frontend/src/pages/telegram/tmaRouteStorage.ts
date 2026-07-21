import type { ActiveRouteSession, RecommendationRouteResponse } from '../../api/recommendations/recommendationRoute.types'

const ROUTE_STORAGE_KEY = 'citygo:tma:activeRoute'
const SESSION_STORAGE_KEY = 'citygo:tma:activeRouteSession'

const isRoute = (value: unknown): value is RecommendationRouteResponse =>
  Boolean(value && typeof value === 'object' && typeof (value as RecommendationRouteResponse).route_id === 'string' && Array.isArray((value as RecommendationRouteResponse).points))

const isSession = (value: unknown): value is ActiveRouteSession => {
  if (!value || typeof value !== 'object') return false
  const session = value as Partial<ActiveRouteSession>
  return typeof session.session_id === 'number'
    && Number.isInteger(session.session_id)
    && session.session_id > 0
    && typeof session.route_id === 'string'
    && Boolean(session.route_id.trim())
    && typeof session.ownership_token === 'string'
    && Boolean(session.ownership_token.trim())
    && typeof session.status === 'string'
    && typeof session.current_point_index === 'number'
    && Array.isArray(session.skipped_place_ids)
    && Array.isArray(session.points)
    && Boolean(session.point_completed_at && typeof session.point_completed_at === 'object')
}

export const restoreTmaRoute = (): RecommendationRouteResponse | null => {
  try {
    const raw = window.localStorage.getItem(ROUTE_STORAGE_KEY)
    if (!raw) return null
    const parsed: unknown = JSON.parse(raw)
    if (!isRoute(parsed)) {
      window.localStorage.removeItem(ROUTE_STORAGE_KEY)
      return null
    }
    return parsed
  } catch {
    try { window.localStorage.removeItem(ROUTE_STORAGE_KEY) } catch { /* ignore */ }
    return null
  }
}

export const saveTmaRoute = (route: RecommendationRouteResponse): void => {
  try {
    window.localStorage.setItem(ROUTE_STORAGE_KEY, JSON.stringify(route))
  } catch {
    // Storage is an optional recovery cache; the current screen remains usable.
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
  if (!isSession(session)) {
    clearTmaRouteSession()
    return
  }
  try {
    window.localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(session))
  } catch {
    // Storage is an optional recovery cache; the current screen remains usable.
  }
}

export const clearTmaRouteSession = (): void => {
  try {
    window.localStorage.removeItem(SESSION_STORAGE_KEY)
  } catch {
    // ignore
  }
}
