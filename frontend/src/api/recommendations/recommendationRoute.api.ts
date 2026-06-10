import { buildApiUrl } from '../../shared/api/http'
import type {
  RecommendationRouteRequest,
  RecommendationRouteResponse,
  UserRouteCorrectionAction,
} from './recommendationRoute.types'

export const buildRecommendationRoute = async (
  payload: RecommendationRouteRequest,
): Promise<RecommendationRouteResponse> => {
  const response = await fetch(buildApiUrl('/v1/user-routes/build'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return response.json()
}

export const sendRouteFeedback = async (
  route: RecommendationRouteResponse,
  rating: number,
  comment?: string,
) => {
  const response = await fetch(buildApiUrl('/route-feedback/'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      route_id: route.route_id,
      user_id: route.context?.user_id ?? null,
      rating,
      comment: comment || null,
      source: 'web',
      problem_types: rating <= 2 ? ['bad_route'] : [],
    }),
  })
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return response.json()
}

export const correctUserRoute = async (
  currentRoute: RecommendationRouteResponse,
  action: UserRouteCorrectionAction,
): Promise<RecommendationRouteResponse> => {
  const firstPlaceId = currentRoute.points[0]?.place_id ?? null
  const response = await fetch(buildApiUrl('/v1/user-routes/correct'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      current_route: currentRoute,
      action,
      target_place_id: action === 'remove_place' ? firstPlaceId : null,
    }),
  })

  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return response.json()
}

export const addPlaceToUserRoute = async (
  currentRoute: RecommendationRouteResponse,
  placeId: string,
  insertAfterPlaceId?: string | null,
): Promise<RecommendationRouteResponse> => {
  const response = await fetch(buildApiUrl(`/v1/user-routes/${currentRoute.route_id}/add-place`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      current_route: currentRoute,
      place_id: placeId,
      insert_after_place_id: insertAfterPlaceId ?? currentRoute.points.at(-1)?.place_id ?? null,
    }),
  })

  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return response.json()
}

export const replacePlaceInUserRoute = async (
  currentRoute: RecommendationRouteResponse,
  oldPlaceId: string,
  newPlaceId: string,
): Promise<RecommendationRouteResponse> => {
  const response = await fetch(buildApiUrl(`/v1/user-routes/${currentRoute.route_id}/replace-place`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      current_route: currentRoute,
      old_place_id: oldPlaceId,
      new_place_id: newPlaceId,
    }),
  })

  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return response.json()
}
