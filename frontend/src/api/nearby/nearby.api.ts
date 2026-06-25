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

export type NearestCitySuggestion = {
  city_slug: string
  city_name: string
  distance_km: number
}

export const getNearbyPlaces = async (
  lat: number,
  lng: number,
  radiusKm = 3,
  signal?: AbortSignal,
): Promise<NearbyPlace[]> => {
  const params = new URLSearchParams({
    lat: String(lat),
    lng: String(lng),
    radius_km: String(radiusKm),
  })

  const response = await fetch(buildApiUrl(`/nearby/?${params.toString()}`), { signal })
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }
  const data: NearbyPlace[] = await response.json()
  return normalizePlaces(data)
}

export const getNearestCitySuggestion = async (
  lat: number,
  lng: number,
): Promise<NearestCitySuggestion | null> => {
  const params = new URLSearchParams({ lat: String(lat), lng: String(lng) })
  const response = await fetch(buildApiUrl(`/nearby/nearest-city?${params.toString()}`))
  if (!response.ok) return null
  return response.json() as Promise<NearestCitySuggestion | null>
}
