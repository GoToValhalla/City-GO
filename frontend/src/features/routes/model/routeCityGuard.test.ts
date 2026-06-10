import { describe, expect, it } from 'vitest'
import { routeMatchesCity } from './routeCityGuard'
import type { RecommendationRouteResponse } from '../../../api/recommendations/recommendationRoute.types'

const route = (citySlug?: string | null): RecommendationRouteResponse => ({
  route_id: 'r',
  status: 'ready',
  total_places: 1,
  total_minutes: 30,
  total_estimated_minutes: 30,
  estimated_distance: 0,
  has_warnings: false,
  warning_count: 0,
  places_with_warnings: [],
  warnings: [],
  points: [{ place_id: '1', city_slug: citySlug, lat: 1, lng: 2, category: 'walk', visit_minutes: 30 }],
  explanation: {},
})

describe('routeMatchesCity', () => {
  it('rejects route points from another city', () => {
    expect(routeMatchesCity(route('zelenogradsk'), 'khanty-mansiysk')).toBe(false)
  })

  it('keeps backward-compatible points without city slug', () => {
    expect(routeMatchesCity(route(null), 'khanty-mansiysk')).toBe(true)
  })
})
