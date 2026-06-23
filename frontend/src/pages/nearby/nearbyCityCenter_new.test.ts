import { describe, expect, it } from 'vitest'
import type { CityOption } from '../../shared/city/currentCity'
import { getNearbyCityCenter } from './nearbyCityCenter'

const city = (overrides: Partial<CityOption>): CityOption => ({
  slug: 'zelenogradsk',
  name: 'Зеленоградск',
  country: 'Россия',
  region: null,
  launch_status: 'published',
  places_count: 0,
  ...overrides,
})

describe('nearby city center', () => {
  it('uses Khanty-Mansiysk coordinates instead of Zelenogradsk fallback', () => {
    const center = getNearbyCityCenter(city({ slug: 'khanty-mansiysk', name: 'Ханты-Мансийск' }))

    expect(center.locationLabel).toBe('Центр Ханты-Мансийск')
    expect(center.lat).toBe(61.0042)
    expect(center.lng).toBe(69.0019)
    expect(center.error).toBeNull()
  })

  it('does not silently fallback to another city when coordinates are missing', () => {
    const center = getNearbyCityCenter(city({ slug: 'unknown-city', name: 'Новый город' }))

    expect(center.locationLabel).toBe('Центр Новый город')
    expect(center.lat).toBeNull()
    expect(center.lng).toBeNull()
    expect(center.error).toBe('Для города Новый город не заданы координаты центра')
  })
})
