import { afterEach, describe, expect, it, vi } from 'vitest'
import { buildRecommendationRoute, correctUserRoute } from './recommendationRoute.api'
import type { RecommendationRouteRequest } from './recommendationRoute.types'

const payload: RecommendationRouteRequest = {
  lat: 54.96, lng: 20.48, time_budget_minutes: 120, interests: ['coffee'],
  avoided_categories: [], excluded_place_ids: [], budget_level: null, pace_mode: null,
  is_visiting: false, city_id: null, visit_city_id: null, visit_days: null, user_id: null,
}

const emptyRoute = {
  route_id: 'r1',
  total_places: 0,
  total_minutes: 0,
  total_estimated_minutes: 0,
  estimated_distance: 0,
  has_warnings: false,
  warning_count: 0,
  places_with_warnings: [],
  warnings: [],
  points: [],
  explanation: {},
}

describe('recommendationRoute.api', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('posts route request to user routes build endpoint', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(emptyRoute), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    const result = await buildRecommendationRoute(payload)

    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/v1/user-routes/build',
      expect.objectContaining({ method: 'POST' }),
    )
    expect(result).toEqual(emptyRoute)
  })

  it('throws error when build response is not ok', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(null, { status: 500 }))

    await expect(buildRecommendationRoute(payload)).rejects.toThrow('HTTP 500')
  })

  it('does not build demo route when backend is unavailable', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Failed to fetch'))

    await expect(buildRecommendationRoute(payload)).rejects.toThrow('Failed to fetch')
  })

  it('posts route correction with first place as remove target', async () => {
    const mockData = { ...emptyRoute, revision: 2 }
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      new Response(JSON.stringify(mockData), { status: 200 }),
    )

    await correctUserRoute({
      ...mockData,
      points: [{ place_id: 'p1', lat: 1, lng: 2, category: 'cafe', visit_minutes: 20 }],
    }, 'remove_place')

    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/v1/user-routes/correct',
      expect.objectContaining({
        body: expect.stringContaining('"target_place_id":"p1"'),
        method: 'POST',
      }),
    )
  })

  it('does not correct demo route when backend is unavailable', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new TypeError('Failed to fetch'))

    await expect(correctUserRoute({ ...emptyRoute, points: [] }, 'extend_route')).rejects.toThrow('Failed to fetch')
  })
})
