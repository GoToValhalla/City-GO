/* @vitest-environment jsdom */
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { ActiveRouteSession, RecommendationRouteResponse } from '../../api/recommendations/recommendationRoute.types'
import { clearTmaRoute, clearTmaRouteSession, restoreTmaRoute, restoreTmaRouteSession, saveTmaRoute, saveTmaRouteSession } from './tmaRouteStorage'

const route = { route_id: 'r1', city_slug: 'zelenogradsk', points: [{ place_id: '1' }] } as unknown as RecommendationRouteResponse

const session: ActiveRouteSession = {
  session_id: 1,
  route_id: 'r1',
  ownership_token: 'owner-token',
  status: 'active',
  current_point_index: 0,
  point_completed_at: {},
  skipped_place_ids: [],
  points: [],
}

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

  it('clears malformed route JSON_new', () => {
    window.localStorage.setItem('citygo:tma:activeRoute', '{not json')
    expect(restoreTmaRoute()).toBeNull()
    expect(window.localStorage.getItem('citygo:tma:activeRoute')).toBeNull()
  })

  it('clears a stored value with no route id or points array_new', () => {
    window.localStorage.setItem('citygo:tma:activeRoute', JSON.stringify({ route_id: 'r1' }))
    expect(restoreTmaRoute()).toBeNull()
    expect(window.localStorage.getItem('citygo:tma:activeRoute')).toBeNull()
  })

  it('does not throw when localStorage is unavailable_new', () => {
    vi.spyOn(window.localStorage.__proto__, 'getItem').mockImplementation(() => { throw new Error('blocked') })
    expect(restoreTmaRoute()).toBeNull()
  })

  it('clearing the route also clears its session_new', () => {
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

  it('persists and restores a session with ownership token_new', () => {
    saveTmaRouteSession(session)
    expect(restoreTmaRouteSession('r1')).toEqual(session)
  })

  it('rejects and clears tokenless legacy session snapshots_new', () => {
    const { ownership_token: _token, ...legacy } = session
    window.localStorage.setItem('citygo:tma:activeRouteSession', JSON.stringify(legacy))
    expect(restoreTmaRouteSession('r1')).toBeNull()
    expect(window.localStorage.getItem('citygo:tma:activeRouteSession')).toBeNull()
  })

  it('rejects blank ownership tokens_new', () => {
    window.localStorage.setItem('citygo:tma:activeRouteSession', JSON.stringify({ ...session, ownership_token: '   ' }))
    expect(restoreTmaRouteSession('r1')).toBeNull()
  })

  it('discards a session for another route_new', () => {
    saveTmaRouteSession(session)
    expect(restoreTmaRouteSession('some-other-route')).toBeNull()
    expect(restoreTmaRouteSession('r1')).toBeNull()
  })

  it('discards malformed stored session JSON_new', () => {
    window.localStorage.setItem('citygo:tma:activeRouteSession', '{not json')
    expect(restoreTmaRouteSession('r1')).toBeNull()
  })

  it('refuses to persist an invalid session_new', () => {
    saveTmaRouteSession({ ...session, ownership_token: '' })
    expect(restoreTmaRouteSession('r1')).toBeNull()
  })

  it('clears the stored session_new', () => {
    saveTmaRouteSession(session)
    clearTmaRouteSession()
    expect(restoreTmaRouteSession('r1')).toBeNull()
  })
})
