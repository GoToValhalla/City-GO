import { describe, expect, it } from 'vitest'
import { RESERVED_CITY_ROUTE_SLUGS, isReservedCityRouteSlug } from './reservedSlugs'

describe('reservedSlugs decision table', () => {
  it.each([
    ['admin', true],
    ['places', true],
    ['routes', true],
    ['zelenogradsk', false],
    ['moscow', false],
    ['', false],
  ])('isReservedCityRouteSlug(%j) → %s', (slug, expected) => {
    expect(isReservedCityRouteSlug(slug)).toBe(expected)
  })

  it('reserved set is closed under lookup', () => {
    for (const slug of RESERVED_CITY_ROUTE_SLUGS) {
      expect(isReservedCityRouteSlug(slug)).toBe(true)
    }
  })
})
