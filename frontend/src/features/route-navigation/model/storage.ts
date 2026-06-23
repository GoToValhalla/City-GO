import type { NavigationPoint, RouteNavigationState } from './types'
import { initialNavigationState } from './types'
import { normalizeNavigationState } from './state'

export const navigationStorageKey = (routeId: number): string =>
  `citygo:route-navigation:${routeId}`

const isState = (value: unknown): value is RouteNavigationState => {
  if (!value || typeof value !== 'object') return false
  const state = value as Partial<RouteNavigationState>
  return (
    (state.status === 'not_started' || state.status === 'active' || state.status === 'completed') &&
    typeof state.currentPointIndex === 'number' &&
    Array.isArray(state.visitedPointIds)
  )
}

export const restoreNavigationState = (
  routeId: number,
  points: NavigationPoint[],
  storage: Storage = window.localStorage,
): RouteNavigationState => {
  const raw = storage.getItem(navigationStorageKey(routeId))
  if (!raw) return initialNavigationState
  try {
    const parsed: unknown = JSON.parse(raw)
    return isState(parsed) ? normalizeNavigationState(parsed, points) : initialNavigationState
  } catch {
    return initialNavigationState
  }
}

export const saveNavigationState = (
  routeId: number,
  state: RouteNavigationState,
  storage: Storage = window.localStorage,
): void => {
  storage.setItem(navigationStorageKey(routeId), JSON.stringify(state))
}

export const clearNavigationState = (
  routeId: number,
  storage: Storage = window.localStorage,
): void => {
  storage.removeItem(navigationStorageKey(routeId))
}
