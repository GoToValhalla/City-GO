import type { NavigationPoint, RouteNavigationEvent, RouteNavigationState } from './types'
import { initialNavigationState } from './types'

const pointIds = (points: NavigationPoint[]): number[] => points.map((point) => point.place_id)

const uniqueKnown = (ids: number[], validIds: number[]): number[] =>
  Array.from(new Set(ids)).filter((id) => validIds.includes(id))

const nextUnvisitedIndex = (
  points: NavigationPoint[],
  visited: number[],
  fromIndex: number,
): number => points.findIndex((point, index) => index >= fromIndex && !visited.includes(point.place_id))

const firstUnvisitedIndex = (points: NavigationPoint[], visited: number[]): number => {
  const index = nextUnvisitedIndex(points, visited, 0)
  return index >= 0 ? index : Math.max(points.length - 1, 0)
}

export const normalizeNavigationState = (
  state: RouteNavigationState | null,
  points: NavigationPoint[],
): RouteNavigationState => {
  if (!state || points.length === 0) return initialNavigationState
  const validIds = pointIds(points)
  const visitedPointIds = uniqueKnown(state.visitedPointIds, validIds)
  const status = visitedPointIds.length === validIds.length ? 'completed' : state.status
  const currentPointIndex = status === 'active'
    ? firstUnvisitedIndex(points, visitedPointIds)
    : Math.min(Math.max(state.currentPointIndex, 0), Math.max(points.length - 1, 0))
  return { status, currentPointIndex, visitedPointIds }
}

export const routeNavigationReducer = (
  state: RouteNavigationState,
  event: RouteNavigationEvent,
  points: NavigationPoint[],
): RouteNavigationState => {
  const normalized = normalizeNavigationState(state, points)
  if (event.type === 'RESET_ROUTE') return initialNavigationState
  if (points.length === 0) return normalized
  if (event.type === 'START_ROUTE') {
    return { ...normalized, status: 'active', currentPointIndex: firstUnvisitedIndex(points, normalized.visitedPointIds) }
  }
  if (event.type === 'COMPLETE_ROUTE') {
    return { status: 'completed', currentPointIndex: points.length - 1, visitedPointIds: pointIds(points) }
  }
  if (normalized.status !== 'active') return normalized
  if (event.type === 'GO_NEXT_POINT') {
    const next = nextUnvisitedIndex(points, normalized.visitedPointIds, normalized.currentPointIndex + 1)
    return { ...normalized, currentPointIndex: next >= 0 ? next : normalized.currentPointIndex }
  }
  const current = points[normalized.currentPointIndex]
  const visitedPointIds = uniqueKnown([...normalized.visitedPointIds, current.place_id], pointIds(points))
  if (visitedPointIds.length === points.length) {
    return { status: 'completed', currentPointIndex: points.length - 1, visitedPointIds }
  }
  return { status: 'active', currentPointIndex: firstUnvisitedIndex(points, visitedPointIds), visitedPointIds }
}
