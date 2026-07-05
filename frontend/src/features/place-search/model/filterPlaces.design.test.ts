import { describe, expect, it } from 'vitest'
import type { Place } from '../../../entities/place/model/types'
import { filterPlaces } from './filterPlaces'

const base: Place[] = [
  { id: 1, slug: 'a', title: 'Кафе у моря', short_description: null, category: 'cafe', address: 'ул. Морская, 1' },
  { id: 2, slug: 'b', title: 'Музей истории', short_description: null, category: 'museum', address: 'ул. Ленина, 10' },
  { id: 3, slug: 'c', title: 'Без категории', short_description: null, category: null, address: 'пр. Победы, 3' },
]

describe('filterPlaces test design', () => {
  it.each(['', '   ', '\t'])('empty-equivalence class %j returns all', (search) => {
    expect(filterPlaces(base, search)).toHaveLength(3)
  })

  it('null category does not crash (regression)', () => {
    expect(() => filterPlaces(base, 'без')).not.toThrow()
    expect(filterPlaces(base, 'победы')).toHaveLength(1)
  })

  it('case-insensitive boundary', () => {
    expect(filterPlaces(base, 'МУЗЕЙ')).toHaveLength(1)
    expect(filterPlaces(base, 'музей')).toHaveLength(1)
  })

  it('no-match negative path', () => {
    expect(filterPlaces(base, 'аэропорт')).toHaveLength(0)
  })

  it('partial substring equivalence', () => {
    expect(filterPlaces(base, 'мор')).toHaveLength(1)
    expect(filterPlaces(base, 'ист')).toHaveLength(1)
  })
})
