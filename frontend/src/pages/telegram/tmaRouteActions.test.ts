/* @vitest-environment jsdom */
import { afterEach, describe, expect, it, vi } from 'vitest'
import * as recommendationApi from '../../api/recommendations/recommendationRoute.api'
import type { RecommendationRouteResponse } from '../../api/recommendations/recommendationRoute.types'
import type { PlaceDetail } from '../../entities/place/model/types'
import { DEFAULT_CITY, setCurrentCity } from '../../shared/city/currentCity'
import { saveLocationSnapshot } from '../../shared/location/storage'
import type { LocationSnapshot } from '../../shared/location/types'
import { addPlaceToTmaRoute, TmaRouteStartUnavailableError } from './tmaRouteActions'
import { restoreTmaRoute } from './tmaRouteStorage'

vi.mock('../../api/recommendations/recommendationRoute.api', () => ({
  buildRecommendationRoute: vi.fn(),
  addPlaceToUserRoute: vi.fn(),
}))

const UNMAPPED_CITY = { slug: 'some-unmapped-city', name: 'Unmapped City', country: 'Россия' }

const place = { id: 42, slug: 'test-place', title: 'Test Place' } as PlaceDetail
const placeWithCoordinates = { id: 42, slug: 'test-place', title: 'Test Place', lat: 55.5, lng: 66.6 } as PlaceDetail

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

const locationSnapshot = (): LocationSnapshot => ({
  coordinates: { latitude: 12.34, longitude: 56.78, accuracy: 10, altitude: null, course: null, speed: null },
  source: 'browser',
  capturedAt: Date.now(),
  stale: false,
})

describe('addPlaceToTmaRoute', () => {
  afterEach(() => {
    window.localStorage.clear()
    window.sessionStorage.clear()
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

  it('uses the supported city coordinates when the city is in the known-center map_new', async () => {
    setCurrentCity(DEFAULT_CITY) // zelenogradsk — has known coordinates
    vi.mocked(recommendationApi.buildRecommendationRoute).mockResolvedValue(routeFixture())
    vi.mocked(recommendationApi.addPlaceToUserRoute).mockResolvedValue(routeFixture())

    await addPlaceToTmaRoute(place)

    const payload = vi.mocked(recommendationApi.buildRecommendationRoute).mock.calls[0][0]
    expect(payload.start_source).toBe('city_center')
    expect(payload.lat).toBeCloseTo(54.96)
    expect(payload.lng).toBeCloseTo(20.48)
  })

  it('uses a previously granted location for a city with no known center (backend-available coordinates)_new', async () => {
    setCurrentCity(UNMAPPED_CITY)
    saveLocationSnapshot(locationSnapshot())
    vi.mocked(recommendationApi.buildRecommendationRoute).mockResolvedValue(routeFixture({ city_slug: UNMAPPED_CITY.slug }))
    vi.mocked(recommendationApi.addPlaceToUserRoute).mockResolvedValue(routeFixture({ city_slug: UNMAPPED_CITY.slug }))

    await addPlaceToTmaRoute(place)

    const payload = vi.mocked(recommendationApi.buildRecommendationRoute).mock.calls[0][0]
    expect(payload.start_source).toBe('current_location')
    expect(payload.lat).toBeCloseTo(12.34)
    expect(payload.lng).toBeCloseTo(56.78)
  })

  it('falls back to the place being added when the city has no known center and location was denied/never granted_new', async () => {
    setCurrentCity(UNMAPPED_CITY)
    // No saveLocationSnapshot call — simulates denied/never-granted location.
    vi.mocked(recommendationApi.buildRecommendationRoute).mockResolvedValue(routeFixture({ city_slug: UNMAPPED_CITY.slug }))
    vi.mocked(recommendationApi.addPlaceToUserRoute).mockResolvedValue(routeFixture({ city_slug: UNMAPPED_CITY.slug }))

    await addPlaceToTmaRoute(placeWithCoordinates)

    const payload = vi.mocked(recommendationApi.buildRecommendationRoute).mock.calls[0][0]
    expect(payload.start_source).toBe('place')
    expect(payload.lat).toBeCloseTo(55.5)
    expect(payload.lng).toBeCloseTo(66.6)
  })

  it('never uses another city coordinates and throws a truthful error when no coordinate source exists_new', async () => {
    setCurrentCity(UNMAPPED_CITY)
    // No location snapshot, and the place itself has no coordinates either.

    await expect(addPlaceToTmaRoute(place)).rejects.toThrow(TmaRouteStartUnavailableError)
    expect(recommendationApi.buildRecommendationRoute).not.toHaveBeenCalled()
  })

  it('the unavailable-start error message is a clear Russian explanation, never silently using another city_new', async () => {
    setCurrentCity(UNMAPPED_CITY)

    try {
      await addPlaceToTmaRoute(place)
      expect.unreachable('expected addPlaceToTmaRoute to throw')
    } catch (err) {
      expect(err).toBeInstanceOf(TmaRouteStartUnavailableError)
      expect((err as Error).message).toContain('Не удалось определить точку старта')
      expect((err as Error).message).not.toContain('zelenogradsk')
    }
  })
})
