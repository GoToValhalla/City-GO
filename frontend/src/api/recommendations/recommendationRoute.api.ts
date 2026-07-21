import { buildApiUrl } from '../../shared/api/http'
import type {
  ActiveRouteAction,
  ActiveRouteSession,
  RecommendationRouteRequest,
  RecommendationRouteResponse,
  UserRouteCorrectionAction,
  UserRouteStructuredBuildResponse,
} from './recommendationRoute.types'

export class ApiRequestError extends Error {
  status: number
  url: string
  method: string
  responseBody: unknown
  requestBody?: unknown

  constructor(params: { status: number; url: string; method: string; responseBody: unknown; requestBody?: unknown }) {
    super(`HTTP ${params.status}`)
    this.name = 'ApiRequestError'
    this.status = params.status
    this.url = params.url
    this.method = params.method
    this.responseBody = params.responseBody
    this.requestBody = params.requestBody
  }
}

const readResponseBody = async (response: Response): Promise<unknown> => {
  const contentType = response.headers.get('content-type') || ''
  try {
    if (contentType.includes('application/json')) return await response.json()
    return await response.text()
  } catch (err) {
    return `Не удалось прочитать тело ответа: ${String(err)}`
  }
}

const assertOk = async (response: Response, params: { url: string; method: string; requestBody?: unknown }) => {
  if (response.ok) return
  throw new ApiRequestError({ status: response.status, url: params.url, method: params.method, responseBody: await readResponseBody(response), requestBody: params.requestBody })
}

const ownershipHeaders = (ownershipToken?: string | null): Record<string, string> => {
  const token = ownershipToken?.trim()
  return token ? { 'X-Route-Session': token } : {}
}

const preserveOwnershipToken = (session: ActiveRouteSession, ownershipToken: string): ActiveRouteSession => ({
  ...session,
  ownership_token: session.ownership_token?.trim() || ownershipToken,
})

const feedbackSource = (): 'web' | 'telegram' => {
  if (typeof window === 'undefined') return 'web'
  return window.location.pathname.startsWith('/telegram') || Boolean(window.Telegram?.WebApp) ? 'telegram' : 'web'
}

export const buildRecommendationRoute = async (payload: RecommendationRouteRequest): Promise<RecommendationRouteResponse> => {
  const url = buildApiUrl('/v1/user-routes/build')
  const response = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) })
  const body = await readResponseBody(response)
  if (!response.ok) throw new ApiRequestError({ status: response.status, url, method: 'POST', responseBody: body, requestBody: payload })
  return body as RecommendationRouteResponse
}

export const buildStructuredRouteOptions = async (payload: RecommendationRouteRequest): Promise<UserRouteStructuredBuildResponse> => {
  const url = buildApiUrl('/v1/user-routes/build-structured')
  const requestBody = { ...payload, slots: payload.route_slots ?? [] }
  const response = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(requestBody) })
  await assertOk(response, { url, method: 'POST', requestBody })
  return response.json()
}

export const sendRouteFeedback = async (route: RecommendationRouteResponse, rating: number, comment?: string, problemTypes: string[] = []) => {
  const url = buildApiUrl('/route-feedback/')
  const normalizedProblems = [...new Set(problemTypes.map((problem) => problem.trim()).filter(Boolean))]
  const requestBody = {
    route_id: route.route_id,
    user_id: route.context?.user_id ?? null,
    rating,
    comment: comment?.trim().slice(0, 1000) || null,
    source: feedbackSource(),
    problem_types: normalizedProblems.length ? normalizedProblems : rating <= 2 ? ['bad_route'] : [],
  }
  const response = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(requestBody) })
  await assertOk(response, { url, method: 'POST', requestBody })
  return response.json()
}

export const correctUserRoute = async (currentRoute: RecommendationRouteResponse, action: UserRouteCorrectionAction, targetPlaceId?: string | null): Promise<RecommendationRouteResponse> => {
  const firstPlaceId = currentRoute.points[0]?.place_id ?? null
  const url = buildApiUrl('/v1/user-routes/correct')
  const requestBody = { current_route: currentRoute, action, target_place_id: targetPlaceId ?? (action === 'remove_place' ? firstPlaceId : null) }
  const response = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(requestBody) })
  await assertOk(response, { url, method: 'POST', requestBody })
  return response.json()
}

export const updateUserRouteOrder = async (currentRoute: RecommendationRouteResponse, orderedPlaceIds: string[]): Promise<RecommendationRouteResponse> => {
  const url = buildApiUrl(`/v1/user-routes/${currentRoute.route_id}/update`)
  const requestBody = { current_route: currentRoute, ordered_place_ids: orderedPlaceIds }
  const response = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(requestBody) })
  await assertOk(response, { url, method: 'POST', requestBody })
  return response.json()
}

export const addPlaceToUserRoute = async (currentRoute: RecommendationRouteResponse, placeId: string, insertAfterPlaceId?: string | null): Promise<RecommendationRouteResponse> => {
  const url = buildApiUrl(`/v1/user-routes/${currentRoute.route_id}/add-place`)
  const requestBody = { current_route: currentRoute, place_id: placeId, insert_after_place_id: insertAfterPlaceId ?? currentRoute.points.at(-1)?.place_id ?? null }
  const response = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(requestBody) })
  await assertOk(response, { url, method: 'POST', requestBody })
  return response.json()
}

export const replacePlaceInUserRoute = async (currentRoute: RecommendationRouteResponse, oldPlaceId: string, newPlaceId: string): Promise<RecommendationRouteResponse> => {
  const url = buildApiUrl(`/v1/user-routes/${currentRoute.route_id}/replace-place`)
  const requestBody = { current_route: currentRoute, old_place_id: oldPlaceId, new_place_id: newPlaceId }
  const response = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(requestBody) })
  await assertOk(response, { url, method: 'POST', requestBody })
  return response.json()
}

export const startActiveRouteSession = async (currentRoute: RecommendationRouteResponse, ownershipToken?: string | null): Promise<ActiveRouteSession> => {
  const url = buildApiUrl(`/v1/user-routes/${currentRoute.route_id}/session/start`)
  const requestBody = { current_route: currentRoute, user_id: currentRoute.context?.user_id ?? null }
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...ownershipHeaders(ownershipToken) },
    body: JSON.stringify(requestBody),
  })
  await assertOk(response, { url, method: 'POST', requestBody })
  const session = await response.json() as ActiveRouteSession
  const token = session.ownership_token?.trim() || ownershipToken?.trim()
  if (!token) throw new Error('Route session ownership token is missing')
  return preserveOwnershipToken(session, token)
}

export const validateActiveRouteSession = async (session: ActiveRouteSession): Promise<void> => {
  const token = session.ownership_token?.trim()
  if (!token) throw new Error('Route session ownership token is missing')
  const url = buildApiUrl(`/route-sessions/${session.session_id}`)
  const response = await fetch(url, { method: 'GET', headers: ownershipHeaders(token) })
  await assertOk(response, { url, method: 'GET' })
  // This endpoint exposes the internal numeric Route.id, while the TMA cache
  // stores the public user-route id encoded in Route.slug. A successful
  // ownership-authenticated read is therefore the authoritative validation;
  // comparing the two different id domains would reject every valid session.
}

export const updateActiveRouteSession = async (session: ActiveRouteSession, action: ActiveRouteAction, placeId?: string | null): Promise<ActiveRouteSession> => {
  const token = session.ownership_token?.trim()
  if (!token) throw new Error('Route session ownership token is missing')
  const url = buildApiUrl(`/v1/user-routes/sessions/${session.session_id}/action`)
  const requestBody = { action, place_id: placeId ?? null }
  const response = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...ownershipHeaders(token) },
    body: JSON.stringify(requestBody),
  })
  await assertOk(response, { url, method: 'POST', requestBody })
  return preserveOwnershipToken(await response.json() as ActiveRouteSession, token)
}
