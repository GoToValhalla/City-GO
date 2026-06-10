import { describe, expect, it } from 'vitest'
import { buildPlacesUrl } from './endpoints'

describe('buildPlacesUrl', () => {
  it('builds URL with city_slug query', () => {
    expect(buildPlacesUrl('zelenogradsk')).toBe('/places/?city_slug=zelenogradsk')
  })
})
