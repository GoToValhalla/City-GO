/* @vitest-environment jsdom */
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ActiveRouteSession, RecommendationRouteResponse } from '../../api/recommendations/recommendationRoute.types'
import { clearTmaRoute, clearTmaRouteSession, restoreTmaRoute, restoreTmaRouteSession, saveTmaRoute, saveTmaRouteSession } from './tmaRouteStorage'

const route = { route_id: 'r1', city_slug: 'zelenogradsk', points: [{ place_id: '1' }] } as unknown as RecommendationRouteResponse

const session = { session_id: 1, route_id: 'r1', status: 'active', current_point_index: 0, point_completed_at: {}, skipped_place_ids: [], points: [] } as ActiveRouteSession

describe('tmaRouteStorage', () => {
  afterEach(() => {
    window.localStorage.clear()
    vi.restoreAllMocks()
  })

  it('returns null when nothing is stored_new', () => {
    expect(restoreTmaRoute()).toBeNull()
  })

  it('persists and restores a route_new', () => {
    saveTmaRoute(route)
    expect(restoreTmaRoute()).toEqual(route)
  })

  it('clears the stored route_new', () => {
    saveTmaRoute(route)
    clearTmaRoute()
    expect(restoreTmaRoute()).toBeNull()
  })

  it('returns null for malformed JSON_new', () => {
    window.localStorage.setItem('citygo:tma:activeRoute', '{not json')
    expect(restoreTmaRoute()).toBeNull()
  })

  it('returns null when the stored value has no points array_new', () => {
    window.localStorage.setItem('citygo:tma:activeRoute', JSON.stringify({ route_id: 'r1' }))
    expect(restoreTmaRoute()).toBeNull()
  })

  it('does not throw when localStorage.getItem is unavailable_new', () => {
    vi.spyOn(window.localStorage.__proto__, 'getItem').mockImplementation(() => { throw new Error('blocked') })
    expect(restoreTmaRoute()).toBeNull()
  })

  it('does not throw when localStorage.setItem is unavailable_new', () => {
    vi.spyOn(window.localStorage.__proto__, 'setItem').mockImplementation(() => { throw new Error('quota exceeded') })
    expect(() => saveTmaRoute(route)).not.toThrow()
  })

  it('clearing the route also clears any stored session (stale local state cleanup)_new', () => {
    saveTmaRoute(route)
    saveTmaRouteSession(session)

    clearTmaRoute()

    expect(restoreTmaRoute()).toBeNull()
    expect(restoreTmaRouteSession('r1')).toBeNull()
  })
})

describe('tmaRouteStorage session', () => {
  afterEach(() => {
    window.localStorage.clear()
    vi.restoreAllMocks()
  })

  it('returns null when nothing is stored_new', () => {
    expect(restoreTmaRouteSession('r1')).toBeNull()
  })

  it('persists and restores a session for the matching route_new', () => {
    saveTmaRouteSession(session)
    expect(restoreTmaRouteSession('r1')).toEqual(session)
  })

  it('discards a session that belongs to a different/stale route_id_new', () => {
    saveTmaRouteSession(session)

    expect(restoreTmaRouteSession('some-other-route')).toBeNull()
    // Reading a mismatched session also clears it — it is stale local state.
    expect(restoreTmaRouteSession('r1')).toBeNull()
  })

  it('discards malformed stored session JSON_new', () => {
    window.localStorage.setItem('citygo:tma:activeRouteSession', '{not json')
    expect(restoreTmaRouteSession('r1')).toBeNull()
  })

  it('discards a stored value missing required session fields_new', () => {
    window.localStorage.setItem('citygo:tma:activeRouteSession', JSON.stringify({ route_id: 'r1' }))
    expect(restoreTmaRouteSession('r1')).toBeNull()
  })

  it('clears the stored session_new', () => {
    saveTmaRouteSession(session)
    clearTmaRouteSession()
    expect(restoreTmaRouteSession('r1')).toBeNull()
  })

  it('does not throw when localStorage is unavailable_new', () => {
    vi.spyOn(window.localStorage.__proto__, 'getItem').mockImplementation(() => { throw new Error('blocked') })
    expect(restoreTmaRouteSession('r1')).toBeNull()
    vi.spyOn(window.localStorage.__proto__, 'setItem').mockImplementation(() => { throw new Error('quota exceeded') })
    expect(() => saveTmaRouteSession(session)).not.toThrow()
  })
})
