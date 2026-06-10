import { buildApiUrl } from '../../shared/api/http'
import type { Place } from '../../entities/place/model/types'
import { normalizePlaces } from '../places/placeNormalizer'

export type OpenNowPlace = Place & {
  city_id: number
  category_id: number | null
  open_time: string
  close_time: string
}

export const getOpenNowPlaces = async (citySlug: string): Promise<OpenNowPlace[]> => {
  const params = new URLSearchParams({ city_slug: citySlug })
  const response = await fetch(buildApiUrl('/open-now/?' + params.toString()))
  if (!response.ok) {
    throw new Error('HTTP ' + response.status)
  }
  const data: OpenNowPlace[] = await response.json()
  return normalizePlaces(data)
}
