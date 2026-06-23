import type { Place } from '../../entities/place/model/types'
import { hasRealAddress, normalizeRawAddress } from '../../shared/place/placeAddress'
import { categoryLabel, timeLabel } from '../../shared/place/categoryLabels'
import { cleanPlaceDescription, verifiedImageUrl } from '../../shared/demo/placePresentation'
import type { PlaceStatus } from '../ui/StatusBadge'

const CLOSED_STATUSES = new Set(['closed', 'temporarily_closed', 'not_found', 'inactive'])
const UNKNOWN_STATUSES = new Set(['unknown', 'unverified', 'needs_recheck', 'needs_review'])

export const placeTitle = (place: Place): string => {
  return (place.title || place.name || 'Место').trim()
}

export const placeDescription = (place: Place): string | null => {
  const raw = (place.short_description ?? place.description ?? '').trim()
  if (!raw || raw === placeTitle(place)) return null
  return cleanPlaceDescription({ ...place, short_description: raw })
}

export const placeImageUrl = (place: Place): string | null => {
  const exactImageUrl = verifiedImageUrl(place)
  if (exactImageUrl) return exactImageUrl
  if (place.photo_url) return place.photo_url
  if (place.image_url) return place.image_url

  const imageUrls = place.image_urls ?? place.photo_urls ?? []
  const firstImageUrl = imageUrls.find((item): item is string => Boolean(item))
  return firstImageUrl ?? null
}

export const placeGallery = (place: Place): string[] => {
  return [
    placeImageUrl(place),
    ...(place.image_urls ?? []),
    ...(place.photo_urls ?? []),
  ].filter((item, index, list): item is string => Boolean(item) && list.indexOf(item) === index)
}

export const placeRating = (place: Place): number | null => {
  const rating = place.rating ?? place.average_rating ?? null
  return typeof rating === 'number' && Number.isFinite(rating) ? rating : null
}

export const placeReviewCount = (place: Place): number | null => {
  const count = place.review_count ?? place.reviews_count ?? null
  return typeof count === 'number' && Number.isFinite(count) && count > 0 ? count : null
}

export const placeDistanceLabel = (place: Place): string | null => {
  if (typeof place.distance_meters === 'number' && Number.isFinite(place.distance_meters)) {
    if (place.distance_meters < 1000) return `${Math.round(place.distance_meters)} м`
    return `${(place.distance_meters / 1000).toFixed(1).replace('.', ',')} км`
  }

  if (typeof place.distance_km === 'number' && Number.isFinite(place.distance_km)) {
    if (place.distance_km < 1) return `${Math.round(place.distance_km * 1000)} м`
    return `${place.distance_km.toFixed(1).replace('.', ',')} км`
  }

  return null
}

export const placeStatus = (place: Place): PlaceStatus => {
  const status = (place.status ?? place.verification_status ?? '').toLowerCase()
  const confidenceLevel = (place.existence_confidence_level ?? '').toLowerCase()

  if ('is_active' in place && place.is_active === false) return 'closed'
  if (CLOSED_STATUSES.has(status) || CLOSED_STATUSES.has(confidenceLevel)) return 'closed'
  if (place.open_time && place.close_time) return 'open'
  if (UNKNOWN_STATUSES.has(status) || UNKNOWN_STATUSES.has(confidenceLevel)) return 'unknown'
  return 'unknown'
}

export const placeAddressLabel = (place: Place): string | null => {
  return hasRealAddress(place.address, place.category) ? normalizeRawAddress(place.address) : null
}

export const placeHoursLabel = (place: Place): string | null => {
  if (place.open_time || place.close_time) return timeLabel(place.open_time ?? undefined, place.close_time ?? undefined)
  if (typeof place.working_hours === 'string' && place.working_hours.trim()) return place.working_hours.trim()
  if (typeof place.opening_hours === 'string' && place.opening_hours.trim()) return place.opening_hours.trim()
  return null
}

export const placeTagLabels = (place: Place): string[] => {
  if (!Array.isArray(place.tags)) return []
  return place.tags
    .map((tag) => typeof tag === 'string' ? categoryLabel(tag) : tag.name ?? categoryLabel(tag.code))
    .filter((tag, index, list) => Boolean(tag) && list.indexOf(tag) === index)
    .slice(0, 5)
}

export const placeFeatureLabels = (place: Place): string[] => {
  return [
    place.indoor ? 'В помещении' : '',
    place.outdoor ? 'На улице' : '',
    place.family_friendly ? 'Для семьи' : '',
    place.dog_friendly ? 'Можно с собакой' : '',
  ].filter(Boolean)
}

export const listText = (value: string | string[] | null | undefined): string | null => {
  if (Array.isArray(value)) {
    const items = value.map((item) => item.trim()).filter(Boolean)
    return items.length ? items.join(', ') : null
  }

  const raw = (value ?? '').trim()
  return raw || null
}

export const placeCategoryLabel = (category: string | null | undefined): string => {
  return categoryLabel(category ?? '')
}
