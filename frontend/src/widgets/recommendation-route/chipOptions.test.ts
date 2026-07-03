import { describe, expect, it } from 'vitest'
import { filterCategoryOptionsForFeatures, getInterestOptionsForFeatures, isRouteBlockedCategoryOption } from './chipOptions'

describe('route feature filtering', () => {
  it('hides sea interest for cities without sea feature', () => {
    const options = getInterestOptionsForFeatures([])

    expect(options.map((item) => item.value)).not.toContain('sea')
  })

  it('hides beach-like categories for cities without sea feature', () => {
    const categories = [
      { code: 'beach', name: 'Пляж' },
      { code: 'museum', name: 'Музей' },
    ]

    expect(filterCategoryOptionsForFeatures(categories, [])).toEqual([{ code: 'museum', name: 'Музей' }])
  })

  it('keeps beach-like categories when sea feature is present', () => {
    const categories = [
      { code: 'beach', name: 'Пляж' },
      { code: 'museum', name: 'Музей' },
    ]

    expect(filterCategoryOptionsForFeatures(categories, ['sea'])).toEqual(categories)
  })

  it('hides route-blocked categories from public route controls', () => {
    const categories = [
      { code: 'cafe', name: 'Кафе' },
      { code: 'health', name: 'Здоровье' },
      { code: 'useful', name: 'Полезное' },
      { code: 'bank', name: 'Банк' },
      { code: 'bus_stop', name: 'Остановка' },
      { code: 'museum', name: 'Музей' },
    ]

    expect(filterCategoryOptionsForFeatures(categories, [])).toEqual([
      { code: 'cafe', name: 'Кафе' },
      { code: 'museum', name: 'Музей' },
    ])
  })

  it('recognizes localized unsafe category labels', () => {
    expect(isRouteBlockedCategoryOption({ code: 'custom-health', name: 'Здоровье' })).toBe(true)
    expect(isRouteBlockedCategoryOption({ code: 'custom-useful', name: 'Полезное' })).toBe(true)
    expect(isRouteBlockedCategoryOption({ code: 'museum', name: 'Музей' })).toBe(false)
  })
})
