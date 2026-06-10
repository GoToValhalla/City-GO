import { buildApiUrl } from '../../shared/api/http'
import type { Place } from '../../entities/place/model/types'
import { normalizePlaces } from '../places/placeNormalizer'

export type NearbyPlace = Place & {
  city_id: number
  category_id: number | null
  lat: number
  lng: number
  distance_km: number
}

export const getNearbyPlaces = async (
  lat: number,
  lng: number,
  radiusKm = 3,
): Promise<NearbyPlace[]> => {
  const params = new URLSearchParams({
    lat: String(lat),
    lng: String(lng),
    radius_km: String(radiusKm),
  })

  const response = await fetch(buildApiUrl(`/nearby/?${params.toString()}`))
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }
  const data: NearbyPlace[] = await response.json()
  return normalizePlaces(data)
}
