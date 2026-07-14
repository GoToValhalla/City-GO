import type { RecommendationRouteResponse } from '../../api/recommendations/recommendationRoute.types'

const STORAGE_KEY = 'citygo:tma:activeRoute'

export const restoreTmaRoute = (): RecommendationRouteResponse | null => {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as RecommendationRouteResponse
    return parsed && typeof parsed === 'object' && Array.isArray(parsed.points) ? parsed : null
  } catch {
    return null
  }
}

export const saveTmaRoute = (route: RecommendationRouteResponse): void => {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(route))
  } catch {
    // localStorage unavailable — route still works for this session, just not restored on reopen.
  }
}

export const clearTmaRoute = (): void => {
  try {
    window.localStorage.removeItem(STORAGE_KEY)
  } catch {
    // ignore
  }
}
