/* @vitest-environment jsdom */
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as recommendationApi from '../../api/recommendations/recommendationRoute.api'
import type { RecommendationRouteResponse } from '../../api/recommendations/recommendationRoute.types'
import type { PlaceDetail } from '../../entities/place/model/types'
import { DEFAULT_CITY, setCurrentCity } from '../../shared/city/currentCity'
import { addPlaceToTmaRoute } from './tmaRouteActions'
import { restoreTmaRoute } from './tmaRouteStorage'

vi.mock('../../api/recommendations/recommendationRoute.api', () => ({
  buildRecommendationRoute: vi.fn(),
  addPlaceToUserRoute: vi.fn(),
}))

const place = { id: 42, slug: 'test-place', title: 'Test Place' } as PlaceDetail

const routeFixture = (overrides: Partial<RecommendationRouteResponse> = {}): RecommendationRouteResponse => ({
  route_id: 'r1',
  city_slug: DEFAULT_CITY.slug,
  total_places: 0,
  total_minutes: 0,
  total_estimated_minutes: 0,
  estimated_distance: 0,
  has_warnings: false,
  warning_count: 0,
  places_with_warnings: [],
  points: [],
  ...overrides,
} as RecommendationRouteResponse)

describe('addPlaceToTmaRoute', () => {
  afterEach(() => {
    window.localStorage.clear()
    vi.clearAllMocks()
    setCurrentCity(DEFAULT_CITY)
  })

  it('builds a fresh route when none is stored, then adds the place_new', async () => {
    const built = routeFixture()
    const withPlace = routeFixture({ points: [{ place_id: '42' }] as never })
    vi.mocked(recommendationApi.buildRecommendationRoute).mockResolvedValue(built)
    vi.mocked(recommendationApi.addPlaceToUserRoute).mockResolvedValue(withPlace)

    const result = await addPlaceToTmaRoute(place)

    expect(recommendationApi.buildRecommendationRoute).toHaveBeenCalledTimes(1)
    expect(recommendationApi.addPlaceToUserRoute).toHaveBeenCalledWith(built, '42')
    expect(result).toEqual(withPlace)
    expect(restoreTmaRoute()).toEqual(withPlace)
  })

  it('reuses the stored route for the same city instead of rebuilding_new', async () => {
    const stored = routeFixture({ route_id: 'existing' })
    window.localStorage.setItem('citygo:tma:activeRoute', JSON.stringify(stored))
    const withPlace = routeFixture({ route_id: 'existing', points: [{ place_id: '42' }] as never })
    vi.mocked(recommendationApi.addPlaceToUserRoute).mockResolvedValue(withPlace)

    await addPlaceToTmaRoute(place)

    expect(recommendationApi.buildRecommendationRoute).not.toHaveBeenCalled()
    expect(recommendationApi.addPlaceToUserRoute).toHaveBeenCalledWith(stored, '42')
  })

  it('rebuilds when the stored route belongs to a different city_new', async () => {
    const stored = routeFixture({ city_slug: 'some-other-city' })
    window.localStorage.setItem('citygo:tma:activeRoute', JSON.stringify(stored))
    const built = routeFixture()
    const withPlace = routeFixture({ points: [{ place_id: '42' }] as never })
    vi.mocked(recommendationApi.buildRecommendationRoute).mockResolvedValue(built)
    vi.mocked(recommendationApi.addPlaceToUserRoute).mockResolvedValue(withPlace)

    await addPlaceToTmaRoute(place)

    expect(recommendationApi.buildRecommendationRoute).toHaveBeenCalledTimes(1)
  })
})
