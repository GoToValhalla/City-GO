import { describe, expect, it } from 'vitest'
import { filterCategoryOptionsForFeatures, getInterestOptionsForFeatures } from './chipOptions'

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
})
