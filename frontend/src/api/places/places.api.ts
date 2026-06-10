import type { Place, PlaceDetail } from '../../entities/place/model/types'
import { buildPlaceBySlugUrl, buildPlacesUrl } from '../../shared/api/endpoints'
import { buildApiUrl } from '../../shared/api/http'
import { normalizePlaceDetail, normalizePlaces } from './placeNormalizer'

// Ответ backend для списка мест с пагинацией.
export type PlacesResponse = {
  items: Place[]
  total: number
  limit: number
  offset: number
}

// Загружает список мест с meta-данными только из backend.
// Demo/local fallback запрещён: публичный продукт должен показывать только данные БД.
export const getPlacesByCityResponse = async (
  citySlug: string,
  limit?: number,
  offset?: number,
): Promise<PlacesResponse> => {
  const response = await fetch(buildApiUrl(buildPlacesUrl(citySlug, limit, offset)))

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }

  const data: PlacesResponse = await response.json()

  return {
    items: Array.isArray(data.items) ? normalizePlaces(data.items) : [],
    total: Number.isFinite(data.total) ? data.total : 0,
    limit: Number.isFinite(data.limit) ? data.limit : 20,
    offset: Number.isFinite(data.offset) ? data.offset : 0,
  }
}

// Загружает список мест по slug города.
// Важно: наружу возвращаем именно массив places, а не весь объект ответа.
export const getPlacesByCity = async (citySlug: string): Promise<Place[]> => {
  const data = await getPlacesByCityResponse(citySlug)
  return data.items
}

// Загружает одно место по slug только из backend.
export const getPlaceBySlug = async (slug: string): Promise<PlaceDetail> => {
  const response = await fetch(buildApiUrl(buildPlaceBySlugUrl(slug)))

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }

  const data: PlaceDetail = await response.json()
  return normalizePlaceDetail(data)
}
