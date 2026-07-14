import { addPlaceToUserRoute, buildRecommendationRoute } from '../../api/recommendations/recommendationRoute.api'
import type { RecommendationRouteResponse } from '../../api/recommendations/recommendationRoute.types'
import type { PlaceDetail } from '../../entities/place/model/types'
import { DEFAULT_CITY, getCurrentCity, getCurrentCityCoordinates } from '../../shared/city/currentCity'
import { restoreTmaRoute, saveTmaRoute } from './tmaRouteStorage'

const resolveStartCoordinates = () => {
  const city = getCurrentCity()
  try {
    return getCurrentCityCoordinates(city.slug)
  } catch {
    return getCurrentCityCoordinates(DEFAULT_CITY.slug)
  }
}

const buildEmptyRoute = async (citySlug: string): Promise<RecommendationRouteResponse> => {
  const coordinates = resolveStartCoordinates()
  return buildRecommendationRoute({
    lat: Number(coordinates.lat),
    lng: Number(coordinates.lng),
    start_source: 'city_center',
    start: { type: 'city_center', lat: Number(coordinates.lat), lng: Number(coordinates.lng), address: null },
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
  const currentRoute = existing && existing.city_slug === city.slug ? existing : await buildEmptyRoute(city.slug)
  const nextRoute = await addPlaceToUserRoute(currentRoute, String(place.id))
  saveTmaRoute(nextRoute)
  return nextRoute
}
