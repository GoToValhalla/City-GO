import { describe, expect, it } from 'vitest'
import {
  filterCategoryOptionsForFeatures,
  filterInterestsForFeatures,
  getInterestOptionsForFeatures,
  getUnsupportedInterestLabels,
} from './chipOptions'

describe('route feature chips', () => {
  it('hides sea interest when city does not support sea feature', () => {
    expect(getInterestOptionsForFeatures([]).map((item) => item.value)).not.toContain('sea')
    expect(filterInterestsForFeatures(['coffee', 'sea', 'museum'], [])).toEqual(['coffee', 'museum'])
    expect(getUnsupportedInterestLabels(['sea'], [])).toEqual(['Море'])
  })

  it('keeps sea interest only for sea-capable city', () => {
    expect(getInterestOptionsForFeatures(['sea']).map((item) => item.value)).toContain('sea')
    expect(filterInterestsForFeatures(['coffee', 'sea'], ['sea'])).toEqual(['coffee', 'sea'])
  })

  it('filters random route categories by city features', () => {
    const categories = [
      { code: 'coffee', name: 'Кофе' },
      { code: 'sea', name: 'Море' },
      { code: 'museum', name: 'Музеи' },
    ]

    expect(filterCategoryOptionsForFeatures(categories, []).map((item) => item.code)).toEqual(['coffee', 'museum'])
    expect(filterCategoryOptionsForFeatures(categories, ['sea']).map((item) => item.code)).toEqual(['coffee', 'sea', 'museum'])
  })
})
