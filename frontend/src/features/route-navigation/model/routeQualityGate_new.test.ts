import { describe, expect, it } from 'vitest'
import type { RoutePoint } from '../../../api/routes/routes.api'
import { evaluateRouteQuality } from './qualityGate'

const point = (overrides: Partial<RoutePoint>): RoutePoint => ({
  place_id: 1,
  position: 1,
  place_title: 'Точка',
  lat: 54.9,
  lng: 20.4,
  category: 'park',
  is_published: true,
  is_route_eligible: true,
  publication_status: 'published',
  is_active: true,
  status: 'active',
  ...overrides,
})

describe('route navigation quality gate', () => {
  it('passes valid route with two points', () => {
    const result = evaluateRouteQuality([point({ place_id: 1 }), point({ place_id: 2 })])
    expect(result.canStart).toBe(true)
    expect(result.validPoints).toHaveLength(2)
  })

  it('blocks route with less than two valid points', () => {
    const result = evaluateRouteQuality([point({ place_id: 1 })])
    expect(result.canStart).toBe(false)
  })

  it('filters missing coordinates', () => {
    const result = evaluateRouteQuality([point({ lat: null }), point({ place_id: 2 })])
    expect(result.counts.missing_coordinates).toBe(1)
    expect(result.validPoints).toHaveLength(1)
  })

  it('filters ineligible, hidden and service categories', () => {
    const result = evaluateRouteQuality([
      point({ place_id: 1, is_route_eligible: false }),
      point({ place_id: 2, is_published: false }),
      point({ place_id: 3, category: 'service' }),
      point({ place_id: 4, category: 'bank' }),
      point({ place_id: 5, category: 'police' }),
      point({ place_id: 6, category: 'mvd' }),
      point({ place_id: 7 }),
      point({ place_id: 8 }),
    ])
    expect(result.counts.route_ineligible).toBe(1)
    expect(result.counts.hidden_place).toBe(1)
    expect(result.counts.service_category).toBe(4)
    expect(result.validPoints.map((item) => item.place_id)).toEqual([7, 8])
  })
})
