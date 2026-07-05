import { describe, expect, it } from 'vitest'
import { cityCatalogPath, cityHomePath, cityPlacePath, cityRouteBuildPath } from './cityPaths'

describe('cityPaths equivalence classes', () => {
  it.each([
    ['zelenogradsk', '/zelenogradsk'],
    ['moscow', '/moscow'],
    ['kutaisi', '/kutaisi'],
  ])('cityHomePath(%s) → %s', (slug, expected) => {
    expect(cityHomePath(slug)).toBe(expected)
  })

  it.each([
    ['zelenogradsk', '/zelenogradsk/catalog'],
    ['astrakhan', '/astrakhan/catalog'],
  ])('cityCatalogPath(%s) → %s', (slug, expected) => {
    expect(cityCatalogPath(slug)).toBe(expected)
  })

  it('cityPlacePath encodes slugs without mutation', () => {
    expect(cityPlacePath('zelenogradsk', 'museum-history')).toBe('/zelenogradsk/places/museum-history')
  })

  it('cityRouteBuildPath is stable', () => {
    expect(cityRouteBuildPath('zelenogradsk')).toBe('/zelenogradsk/routes/build')
  })
})
