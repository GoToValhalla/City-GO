import { describe, expect, it } from 'vitest'
import type { Place } from '../../entities/place/model/types'
import { buildYandexMapUrl, buildYandexWidgetUrl, placeCoordinate, placesWithCoordinates } from './yandexMaps'

const place = (overrides: Partial<Place>): Place => ({
  id: 1,
  slug: 'test-place',
  title: 'Тестовое место',
  short_description: null,
  category: 'museum',
  address: null,
  ...overrides,
})

describe('yandex map helpers', () => {
  it('filters places without coordinates', () => {
    const valid = place({ id: 1, lat: 54.7, lng: 20.5 })
    const invalid = place({ id: 2, lat: null, lng: 20.6 })

    expect(placeCoordinate(valid)).toEqual({ lat: 54.7, lng: 20.5 })
    expect(placeCoordinate(invalid)).toBeNull()
    expect(placesWithCoordinates([valid, invalid])).toEqual([valid])
  })

  it('builds widget url with active marker', () => {
    const url = buildYandexWidgetUrl({
      center: { lat: 54.7, lng: 20.5 },
      activePlaceId: 2,
      places: [
        place({ id: 1, lat: 54.7, lng: 20.5 }),
        place({ id: 2, lat: 54.8, lng: 20.6 }),
      ],
    })

    expect(url).toContain('https://yandex.ru/map-widget/v1/')
    expect(decodeURIComponent(url)).toContain('20.5,54.7,pm2vvm')
    expect(decodeURIComponent(url)).toContain('20.6,54.8,pm2rdm')
  })

  it('builds fallback single point marker when there are no places', () => {
    const url = buildYandexWidgetUrl({ center: { lat: 54.7, lng: 20.5 }, zoom: 16 })

    expect(decodeURIComponent(url)).toContain('pt=20.5,54.7,pm2rdm')
    expect(url).toContain('z=16')
  })

  it('builds external map url for active place', () => {
    const url = buildYandexMapUrl({
      center: { lat: 54.7, lng: 20.5 },
      activePlaceId: 2,
      places: [place({ id: 2, lat: 54.8, lng: 20.6 })],
      zoom: 16,
    })

    expect(url).toBe('https://yandex.ru/maps/?pt=20.6,54.8&z=16&l=map')
  })
})
