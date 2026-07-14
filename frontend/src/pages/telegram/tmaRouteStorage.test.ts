/* @vitest-environment jsdom */
import { afterEach, describe, expect, it, vi } from 'vitest'
import type { RecommendationRouteResponse } from '../../api/recommendations/recommendationRoute.types'
import { clearTmaRoute, restoreTmaRoute, saveTmaRoute } from './tmaRouteStorage'

const route = { route_id: 'r1', city_slug: 'zelenogradsk', points: [{ place_id: '1' }] } as unknown as RecommendationRouteResponse

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
})
