import { describe, expect, it } from 'vitest'
import type { CityOption } from '../../../shared/city/currentCity'
import { cityIdentity, cityLocation, filterCities } from './citySearch'

const cities: CityOption[] = [
  { slug: 'pushkin-spb', name: 'Пушкин', region: 'Санкт-Петербург', country: 'Россия' },
  { slug: 'pushkin-saratov', name: 'Пушкин', region: 'Саратовская область', country: 'Россия' },
  { slug: 'almaty', name: 'Алматы', region: 'Алматы', country: 'Казахстан' },
]

describe('city search', () => {
  it('shows a stable identity for cities with the same name', () => {
    expect(cityIdentity(cities[0])).toBe('Пушкин · Санкт-Петербург · Россия')
    expect(cityIdentity(cities[1])).toBe('Пушкин · Саратовская область · Россия')
  })

  it('does not repeat a region that equals the country', () => {
    expect(cityLocation({ slug: 'x', name: 'X', region: 'Россия', country: 'Россия' })).toBe('Россия')
  })

  it('searches by city, region, country and slug', () => {
    expect(filterCities(cities, 'саратов').map((city) => city.slug)).toEqual(['pushkin-saratov'])
    expect(filterCities(cities, 'казахстан').map((city) => city.slug)).toEqual(['almaty'])
    expect(filterCities(cities, 'pushkin-spb').map((city) => city.slug)).toEqual(['pushkin-spb'])
  })
})
