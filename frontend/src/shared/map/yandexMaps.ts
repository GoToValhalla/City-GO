import type { Place } from '../../entities/place/model/types'

export type MapCoordinate = {
  lat: number
  lng: number
}

const isFiniteNumber = (value: unknown): value is number => typeof value === 'number' && Number.isFinite(value)

export const placeCoordinate = (place: Place): MapCoordinate | null => {
  if (!isFiniteNumber(place.lat) || !isFiniteNumber(place.lng)) return null
  return { lat: place.lat, lng: place.lng }
}

export const placesWithCoordinates = (places: Place[]) => places.filter((place) => placeCoordinate(place) !== null)

const markerStyle = (active: boolean) => (active ? 'pm2rdm' : 'pm2vvm')

export const buildYandexWidgetUrl = (params: {
  center: MapCoordinate
  places?: Place[]
  activePlaceId?: number | null
  zoom?: number
}) => {
  const zoom = params.zoom ?? 13
  const points = (params.places ?? [])
    .slice(0, 50)
    .map((place) => {
      const coord = placeCoordinate(place)
      if (!coord) return null
      return `${coord.lng},${coord.lat},${markerStyle(place.id === params.activePlaceId)}`
    })
    .filter(Boolean)
    .join('~')

  const query = new URLSearchParams({
    ll: `${params.center.lng},${params.center.lat}`,
    z: String(zoom),
  })
  if (points) query.set('pt', points)
  return `https://yandex.ru/map-widget/v1/?${query.toString()}`
}

export const buildYandexMapUrl = (params: {
  center: MapCoordinate
  places?: Place[]
  activePlaceId?: number | null
  zoom?: number
}) => {
  const zoom = params.zoom ?? 13
  const active = (params.places ?? []).find((place) => place.id === params.activePlaceId)
  const activeCoord = active ? placeCoordinate(active) : null
  const point = activeCoord ? `${activeCoord.lng},${activeCoord.lat}` : `${params.center.lng},${params.center.lat}`
  return `https://yandex.ru/maps/?pt=${point}&z=${zoom}&l=map`
}
