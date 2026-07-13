import { describe, expect, it } from 'vitest'
import { buildRandomRoutePlan, parseRandomRouteMode } from './randomRoutePlan'

describe('random route plan', () => {
  it('keeps duration and removes categories for random places', () => {
    expect(buildRandomRoutePlan('random_places', ['cafe'], 90, 42)).toEqual({
      seed: 42, minutes: 90, categoryMode: 'none', categories: [],
    })
  })

  it('chooses a deterministic duration and one to three real categories for a mood', () => {
    const first = buildRandomRoutePlan('random_mood', ['park', 'cafe', 'museum', 'cafe'], 90, 42)
    const second = buildRandomRoutePlan('random_mood', ['museum', 'cafe', 'park'], 180, 42)
    expect(first).toEqual(second)
    expect([60, 120, 180, 240]).toContain(first.minutes)
    expect(first.categoryMode).toBe('balanced')
    expect(first.categories.length).toBeGreaterThanOrEqual(1)
    expect(first.categories.length).toBeLessThanOrEqual(3)
    expect(first.categories.every((category) => ['park', 'cafe', 'museum'].includes(category))).toBe(true)
  })

  it('uses random places as the safe default for unknown query values', () => {
    expect(parseRandomRouteMode('random_mood')).toBe('random_mood')
    expect(parseRandomRouteMode('unknown')).toBe('random_places')
  })
})
