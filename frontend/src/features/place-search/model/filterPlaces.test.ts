import { describe, expect, it } from 'vitest'
import type { Place } from '../../../entities/place/model/types'
import { filterPlaces } from './filterPlaces'

const places: Place[] = [
  {
    id: 1,
    slug: 'a',
    title: 'Кафе у моря',
    short_description: null,
    category: 'cafe',
    address: 'ул. Морская, 1',
  },
  {
    id: 2,
    slug: 'b',
    title: 'Музей истории',
    short_description: null,
    category: 'museum',
    address: 'ул. Ленина, 10',
  },
]

describe('filterPlaces', () => {
  it('returns all places for empty search', () => {
    expect(filterPlaces(places, '')).toHaveLength(2)
  })

  it('filters by title/category/address', () => {
    expect(filterPlaces(places, 'музей')).toHaveLength(1)
    expect(filterPlaces(places, 'cafe')).toHaveLength(1)
    expect(filterPlaces(places, 'морская')).toHaveLength(1)
  })
})
