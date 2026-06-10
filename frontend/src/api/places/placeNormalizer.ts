import type { Place, PlaceDetail } from '../../entities/place/model/types'
import { hasRealAddress, normalizeRawAddress, UNCLEAR_ADDRESS_LABEL } from '../../shared/place/placeAddress'

export const normalizePlace = <T extends Place>(place: T): T => {
  const visit = place.visit_minutes ?? place.average_visit_duration_minutes ?? undefined
  return { ...place, visit_minutes: visit, address: normalizeAddress(place) }
}

export const normalizePlaces = <T extends Place>(places: T[]): T[] => {
  return places.map(normalizePlace)
}

export const normalizePlaceDetail = (place: PlaceDetail): PlaceDetail => {
  return normalizePlace(place)
}

const normalizeAddress = (place: Place): string => {
  const raw = normalizeRawAddress(place.address)
  return hasRealAddress(raw, place.category) ? raw : UNCLEAR_ADDRESS_LABEL
}
