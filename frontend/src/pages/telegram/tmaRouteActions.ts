import { addPlaceToUserRoute, buildRecommendationRoute } from '../../api/recommendations/recommendationRoute.api'
import type { RecommendationRouteResponse } from '../../api/recommendations/recommendationRoute.types'
import type { PlaceDetail } from '../../entities/place/model/types'
import { getCurrentCity, getCurrentCityCoordinates } from '../../shared/city/currentCity'
import { restoreLocationSnapshot } from '../../shared/location/storage'
import { restoreTmaRoute, saveTmaRoute } from './tmaRouteStorage'

export class TmaRouteStartUnavailableError extends Error {
  constructor() {
    super('Не удалось определить точку старта для этого города. Постройте маршрут, начав с конкретного места, или включите геолокацию.')
    this.name = 'TmaRouteStartUnavailableError'
  }
}

type StartCoordinates = { lat: number; lng: number; source: 'city_center' | 'place' | 'current_location' }

/** Never falls back to another city's coordinates (no cross-city fallback).
 * Order: 1) this city's known center (existing hardcoded map — no new list
 * added here), 2) a previously granted location, if the user already
 * shared one (restoreLocationSnapshot never actively requests permission —
 * a denied/never-granted location just means this tier is skipped, it
 * never blocks), 3) the place actually being added right now (real
 * backend data, not a guess), 4) give up truthfully — the backend has no
 * coordinate-less build mode (UserRouteIntent.lat/lng are required). */
const resolveStartCoordinates = (place: PlaceDetail): StartCoordinates => {
  const city = getCurrentCity()
  try {
    const cityCoordinates = getCurrentCityCoordinates(city.slug)
    return { lat: Number(cityCoordinates.lat), lng: Number(cityCoordinates.lng), source: 'city_center' }
  } catch {
    // This city has no known center — fall through to other sources.
  }
  const locationSnapshot = restoreLocationSnapshot()
  if (locationSnapshot) {
    return { lat: locationSnapshot.coordinates.latitude, lng: locationSnapshot.coordinates.longitude, source: 'current_location' }
  }
  if (typeof place.lat === 'number' && typeof place.lng === 'number' && Number.isFinite(place.lat) && Number.isFinite(place.lng)) {
    return { lat: place.lat, lng: place.lng, source: 'place' }
  }
  throw new TmaRouteStartUnavailableError()
}

const buildEmptyRoute = async (citySlug: string, place: PlaceDetail): Promise<RecommendationRouteResponse> => {
  const coordinates = resolveStartCoordinates(place)
  return buildRecommendationRoute({
    lat: coordinates.lat,
    lng: coordinates.lng,
    start_source: coordinates.source,
    start: { type: coordinates.source, lat: coordinates.lat, lng: coordinates.lng, address: null },
    time_budget_minutes: 120,
    interests: [],
    avoided_categories: [],
    excluded_place_ids: [],
    budget_level: null,
    pace_mode: null,
    is_visiting: false,
    city_id: citySlug,
    visit_city_id: null,
    visit_days: null,
  })
}

export const addPlaceToTmaRoute = async (place: PlaceDetail): Promise<RecommendationRouteResponse> => {
  const city = getCurrentCity()
  const existing = restoreTmaRoute()
  const currentRoute = existing && existing.city_slug === city.slug ? existing : await buildEmptyRoute(city.slug, place)
  const nextRoute = await addPlaceToUserRoute(currentRoute, String(place.id))
  saveTmaRoute(nextRoute)
  return nextRoute
}
