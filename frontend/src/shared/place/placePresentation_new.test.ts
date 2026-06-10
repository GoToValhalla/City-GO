/**
 * tests for cleanPlaceDescription — Russian and Latin prefix stripping.
 * suffix: _new (per project convention)
 */
import { describe, expect, it } from 'vitest'
import { cleanPlaceDescription } from './placePresentation'
import type { Place } from '../../entities/place/model/types'

const makePlace = (short_description: string | null, category = 'food', title = 'Some Place'): Place =>
  ({ short_description, category, title } as Place)

describe('cleanPlaceDescription_new', () => {
  it('strips Russian prefix "Еда:"', () => {
    const result = cleanPlaceDescription(makePlace('Еда: Beer Zelis'))
    expect(result).toBe('Beer Zelis')
  })

  it('strips Russian prefix "Кафе:"', () => {
    const result = cleanPlaceDescription(makePlace('Кафе: Название'))
    expect(result).toBe('Название')
  })

  it('strips Latin prefix "food:"', () => {
    const result = cleanPlaceDescription(makePlace('food: Beer Zelis'))
    expect(result).toBe('Beer Zelis')
  })

  it('leaves normal description without prefix unchanged', () => {
    const result = cleanPlaceDescription(makePlace('Красивое место на набережной'))
    expect(result).toBe('Красивое место на набережной')
  })

  it('strips prefix "Кофе:"', () => {
    const result = cleanPlaceDescription(makePlace('Кофе: Тихое место для работы'))
    expect(result).toBe('Тихое место для работы')
  })

  it('strips prefix "Музей:"', () => {
    const result = cleanPlaceDescription(makePlace('Музей: Янтарный музей'))
    expect(result).toBe('Янтарный музей')
  })

  it('returns generic fallback when description matches title', () => {
    const result = cleanPlaceDescription(makePlace('Музей: Some Place', 'museum', 'Some Place'))
    expect(result).not.toBe('Some Place')
  })

  it('returns generic fallback for null description', () => {
    const result = cleanPlaceDescription(makePlace(null, 'park'))
    expect(result.length).toBeGreaterThan(0)
  })
})
