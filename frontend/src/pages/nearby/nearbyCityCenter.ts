import { getCurrentCityCoordinates, type CityOption } from '../../shared/city/currentCity'

export type NearbyCityCenter = {
  lat: number | null
  lng: number | null
  locationLabel: string
  error: string | null
}

export const getNearbyCityCenter = (city: CityOption): NearbyCityCenter => {
  try {
    const coordinates = getCurrentCityCoordinates(city.slug)
    const lat = Number(coordinates.lat)
    const lng = Number(coordinates.lng)

    if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
      throw new Error(`Некорректные координаты города: ${city.slug}`)
    }

    return {
      lat,
      lng,
      locationLabel: `Центр ${city.name}`,
      error: null,
    }
  } catch {
    return {
      lat: null,
      lng: null,
      locationLabel: `Центр ${city.name}`,
      error: `Для города ${city.name} не заданы координаты центра`,
    }
  }
}
