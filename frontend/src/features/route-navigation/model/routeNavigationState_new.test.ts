/* @vitest-environment jsdom */
import { describe, expect, it } from 'vitest'
import { normalizeNavigationState, routeNavigationReducer } from './state'
import { restoreNavigationState, saveNavigationState } from './storage'
import type { NavigationPoint, RouteNavigationState } from './types'

const points: NavigationPoint[] = [
  { place_id: 1, position: 1, place_title: 'Парк', lat: 1, lng: 1, navigationIndex: 0 },
  { place_id: 2, position: 2, place_title: 'Музей', lat: 2, lng: 2, navigationIndex: 1 },
]

const active: RouteNavigationState = { status: 'active', currentPointIndex: 0, visitedPointIds: [] }

describe('route navigation state machine', () => {
  it('starts route at first unvisited point', () => {
    const state = routeNavigationReducer({ status: 'not_started', currentPointIndex: 0, visitedPointIds: [] }, { type: 'START_ROUTE' }, points)
    expect(state).toEqual({ status: 'active', currentPointIndex: 0, visitedPointIds: [] })
  })

  it('marks current point visited and advances', () => {
    const state = routeNavigationReducer(active, { type: 'MARK_CURRENT_VISITED' }, points)
    expect(state.visitedPointIds).toEqual([1])
    expect(state.currentPointIndex).toBe(1)
  })

  it('moves to next point and completes on last point', () => {
    const next = routeNavigationReducer(
      { status: 'active', currentPointIndex: 0, visitedPointIds: [1] },
      { type: 'GO_NEXT_POINT' },
      points,
    )
    expect(next.currentPointIndex).toBe(1)
    const done = routeNavigationReducer(next, { type: 'MARK_CURRENT_VISITED' }, points)
    expect(done.status).toBe('completed')
    expect(done.visitedPointIds).toEqual([1, 2])
  })

  it('completes and resets route', () => {
    const done = routeNavigationReducer(active, { type: 'COMPLETE_ROUTE' }, points)
    expect(done.status).toBe('completed')
    expect(done.visitedPointIds).toEqual([1, 2])
    expect(routeNavigationReducer(done, { type: 'RESET_ROUTE' }, points).status).toBe('not_started')
  })

  it('normalizes stale saved state and restores from localStorage', () => {
    const storage = window.localStorage
    storage.clear()
    saveNavigationState(7, { status: 'active', currentPointIndex: 9, visitedPointIds: [1, 999] }, storage)
    expect(restoreNavigationState(7, points, storage)).toEqual({ status: 'active', currentPointIndex: 1, visitedPointIds: [1] })
    expect(normalizeNavigationState({ status: 'completed', currentPointIndex: 9, visitedPointIds: [1, 2, 3] }, points).visitedPointIds).toEqual([1, 2])
  })
})
