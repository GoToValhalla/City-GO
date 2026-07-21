import { afterEach, describe, expect, it, vi } from 'vitest'
import {
  buildRecommendationRoute,
  correctUserRoute,
  startActiveRouteSession,
  updateActiveRouteSession,
  validateActiveRouteSession,
} from './recommendationRoute.api'
import type { ActiveRouteSession, RecommendationRouteRequest, RecommendationRouteResponse } from './recommendationRoute.types'

const payload: RecommendationRouteRequest = {
  lat: 54.96, lng: 20.48, time_budget_minutes: 120, interests: ['coffee'],
  avoided_categories: [], excluded_place_ids: [], budget_level: null, pace_mode: null,
  is_visiting: false, city_id: null, visit_city_id: null, visit_days: null, user_id: null,
}

const emptyRoute: RecommendationRouteResponse = {
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

const session: ActiveRouteSession = {
  session_id: 7,
  route_id: 'r1',
  ownership_token: 'owner-token',
  status: 'active',
  current_point_index: 0,
  point_completed_at: {},
  skipped_place_ids: [],
  points: [],
}

describe('recommendationRoute.api', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('posts route request to user routes build endpoint', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(emptyRoute), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }))

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
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(mockData), { status: 200 }))

    await correctUserRoute({
      ...mockData,
      points: [{ place_id: 'p1', lat: 1, lng: 2, category: 'cafe', visit_minutes: 20 }],
    }, 'remove_place')

    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/v1/user-routes/correct',
      expect.objectContaining({ body: expect.stringContaining('"target_place_id":"p1"'), method: 'POST' }),
    )
  })

  it('requires a new session response to contain an ownership token_new', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ ...session, ownership_token: '' }), { status: 200 }))
    await expect(startActiveRouteSession(emptyRoute)).rejects.toThrow('ownership token is missing')
  })

  it('sends ownership header on session reclaim and preserves the supplied token_new', async () => {
    const { ownership_token: _ownershipToken, ...responseSession } = session
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(responseSession), { status: 200 }))
    const result = await startActiveRouteSession(emptyRoute, 'owner-token')
    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/v1/user-routes/r1/session/start',
      expect.objectContaining({ headers: expect.objectContaining({ 'X-Route-Session': 'owner-token' }) }),
    )
    expect(result.ownership_token).toBe('owner-token')
  })

  it('sends ownership header on session action and preserves token when omitted_new', async () => {
    const { ownership_token: _ownershipToken, ...responseSession } = session
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify(responseSession), { status: 200 }))
    const result = await updateActiveRouteSession(session, 'pause')
    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/v1/user-routes/sessions/7/action',
      expect.objectContaining({ headers: expect.objectContaining({ 'X-Route-Session': 'owner-token' }) }),
    )
    expect(result.ownership_token).toBe('owner-token')
  })

  it('validates restored session through the ownership-protected canonical endpoint_new', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ route_id: 42 }), { status: 200 }))
    await validateActiveRouteSession(session)
    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/route-sessions/7',
      { method: 'GET', headers: { 'X-Route-Session': 'owner-token' } },
    )
  })

  it('rejects restored session when ownership validation fails_new', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response(JSON.stringify({ detail: 'Route session not found' }), {
      status: 404,
      headers: { 'Content-Type': 'application/json' },
    }))
    await expect(validateActiveRouteSession(session)).rejects.toMatchObject({ status: 404 })
  })

  it('fails locally before requests when an ownership token is missing_new', async () => {
    const tokenless = { ...session, ownership_token: undefined }
    const fetchMock = vi.spyOn(globalThis, 'fetch')
    await expect(validateActiveRouteSession(tokenless)).rejects.toThrow('ownership token is missing')
    await expect(updateActiveRouteSession(tokenless, 'pause')).rejects.toThrow('ownership token is missing')
    expect(fetchMock).not.toHaveBeenCalled()
  })
})
