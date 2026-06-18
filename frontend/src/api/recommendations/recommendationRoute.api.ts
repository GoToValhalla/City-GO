import { buildApiUrl } from '../../shared/api/http'
import type {
  RecommendationRouteRequest,
  RecommendationRouteResponse,
  UserRouteCorrectionAction,
} from './recommendationRoute.types'

export class ApiRequestError extends Error {
  status: number
  url: string
  method: string
  responseBody: string
  requestBody?: unknown

  constructor(params: {
    status: number
    url: string
    method: string
    responseBody: string
    requestBody?: unknown
  }) {
    super(`HTTP ${params.status}`)
    this.name = 'ApiRequestError'
    this.status = params.status
    this.url = params.url
    this.method = params.method
    this.responseBody = params.responseBody
    this.requestBody = params.requestBody
  }
}

const readErrorBody = async (response: Response): Promise<string> => {
  const contentType = response.headers.get('content-type') || ''
  try {
    if (contentType.includes('application/json')) {
      return JSON.stringify(await response.json(), null, 2)
    }
    return await response.text()
  } catch (err) {
    return `Не удалось прочитать тело ответа: ${String(err)}`
  }
}

const assertOk = async (
  response: Response,
  params: { url: string; method: string; requestBody?: unknown },
) => {
  if (response.ok) return
  throw new ApiRequestError({
    status: response.status,
    url: params.url,
    method: params.method,
    responseBody: await readErrorBody(response),
    requestBody: params.requestBody,
  })
}

export const buildRecommendationRoute = async (
  payload: RecommendationRouteRequest,
): Promise<RecommendationRouteResponse> => {
  const url = buildApiUrl('/v1/user-routes/build')
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  await assertOk(response, { url, method: 'POST', requestBody: payload })
  return response.json()
}

export const sendRouteFeedback = async (
  route: RecommendationRouteResponse,
  rating: number,
  comment?: string,
) => {
  const url = buildApiUrl('/route-feedback/')
  const requestBody = {
    route_id: route.route_id,
    user_id: route.context?.user_id ?? null,
    rating,
    comment: comment || null,
    source: 'web',
    problem_types: rating <= 2 ? ['bad_route'] : [],
  }
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(requestBody),
  })
  await assertOk(response, { url, method: 'POST', requestBody })
  return response.json()
}

export const correctUserRoute = async (
  currentRoute: RecommendationRouteResponse,
  action: UserRouteCorrectionAction,
): Promise<RecommendationRouteResponse> => {
  const firstPlaceId = currentRoute.points[0]?.place_id ?? null
  const url = buildApiUrl('/v1/user-routes/correct')
  const requestBody = {
    current_route: currentRoute,
    action,
    target_place_id: action === 'remove_place' ? firstPlaceId : null,
  }
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(requestBody),
  })

  await assertOk(response, { url, method: 'POST', requestBody })
  return response.json()
}

export const addPlaceToUserRoute = async (
  currentRoute: RecommendationRouteResponse,
  placeId: string,
  insertAfterPlaceId?: string | null,
): Promise<RecommendationRouteResponse> => {
  const url = buildApiUrl(`/v1/user-routes/${currentRoute.route_id}/add-place`)
  const requestBody = {
    current_route: currentRoute,
    place_id: placeId,
    insert_after_place_id: insertAfterPlaceId ?? currentRoute.points.at(-1)?.place_id ?? null,
  }
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(requestBody),
  })

  await assertOk(response, { url, method: 'POST', requestBody })
  return response.json()
}

export const replacePlaceInUserRoute = async (
  currentRoute: RecommendationRouteResponse,
  oldPlaceId: string,
  newPlaceId: string,
): Promise<RecommendationRouteResponse> => {
  const url = buildApiUrl(`/v1/user-routes/${currentRoute.route_id}/replace-place`)
  const requestBody = {
    current_route: currentRoute,
    old_place_id: oldPlaceId,
    new_place_id: newPlaceId,
  }
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(requestBody),
  })

  await assertOk(response, { url, method: 'POST', requestBody })
  return response.json()
}
