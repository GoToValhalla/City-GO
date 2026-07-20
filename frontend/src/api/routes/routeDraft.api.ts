import { buildApiUrl } from '../../shared/api/http'
import type { CategoryOption, RouteDraft, RouteDraftSearchItem } from './routeDraft.types'

const jsonHeaders = { 'Content-Type': 'application/json' }
export const ROUTE_DRAFT_SESSION_HEADER = 'X-Route-Draft-Session'

const readJson = async <T>(response: Response): Promise<T> => {
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return response.json() as Promise<T>
}

const sessionHeaders = (sessionToken: string) => ({
  ...jsonHeaders,
  [ROUTE_DRAFT_SESSION_HEADER]: sessionToken,
})

/** Require Web Crypto; never fall back to Math.random. */
export const createRouteDraftSessionToken = (): string => {
  if (typeof crypto === 'undefined' || typeof crypto.randomUUID !== 'function') {
    throw new Error('Secure crypto.randomUUID is required for draft session tokens')
  }
  return `${crypto.randomUUID()}${crypto.randomUUID()}`.replace(/-/g, '').slice(0, 64)
}

export type RouteDraftCreateResult = {
  draft: RouteDraft
  ownershipToken: string
}

export const createRandomDraft = async (payload: {
  city_slug: string
  budget_minutes: number
  selected_category_slugs: string[]
  category_mode: 'none' | 'balanced'
  seed?: number
}): Promise<RouteDraftCreateResult> => {
  const response = await fetch(buildApiUrl('/routes/random'), {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({
      ...payload,
      start: { type: 'city_center', label: 'Центр города' },
    }),
  })
  const body = await readJson<RouteDraft & { ownership_token?: string }>(response)
  const ownershipToken =
    body.ownership_token || response.headers.get(ROUTE_DRAFT_SESSION_HEADER) || ''
  if (!ownershipToken) {
    throw new Error('Server did not return ownership_token for route draft')
  }
  const { ownership_token: _ignored, ...draft } = body
  return { draft: draft as RouteDraft, ownershipToken }
}

export const removeDraftPoint = async (
  draft: RouteDraft,
  pointId: number,
  sessionToken: string,
): Promise<RouteDraft> => {
  const response = await fetch(buildApiUrl(`/routes/drafts/${draft.draft_id}/remove-point`), {
    method: 'POST',
    headers: sessionHeaders(sessionToken),
    body: JSON.stringify({ point_id: pointId, version: draft.version }),
  })
  return readJson<RouteDraft>(response)
}

export const searchDraftPlaces = async (
  draft: RouteDraft,
  q: string,
  sessionToken: string,
): Promise<RouteDraftSearchItem[]> => {
  const query = new URLSearchParams({ q, limit: '8' })
  const response = await fetch(buildApiUrl(`/routes/drafts/${draft.draft_id}/search-places?${query}`), {
    headers: { [ROUTE_DRAFT_SESSION_HEADER]: sessionToken },
  })
  return readJson<{ items: RouteDraftSearchItem[] }>(response).then((payload) => payload.items)
}

export const addDraftPoint = async (
  draft: RouteDraft,
  placeId: number,
  sessionToken: string,
): Promise<RouteDraft> => {
  const response = await fetch(buildApiUrl(`/routes/drafts/${draft.draft_id}/add-point`), {
    method: 'POST',
    headers: sessionHeaders(sessionToken),
    body: JSON.stringify({
      place_id: placeId,
      after_position: draft.points.at(-1)?.position ?? null,
      version: draft.version,
    }),
  })
  return readJson<RouteDraft>(response)
}

export const replaceDraftPoint = async (
  draft: RouteDraft,
  pointId: number,
  placeId: number,
  sessionToken: string,
): Promise<RouteDraft> => {
  const response = await fetch(buildApiUrl(`/routes/drafts/${draft.draft_id}/replace-point`), {
    method: 'POST',
    headers: sessionHeaders(sessionToken),
    body: JSON.stringify({
      point_id: pointId,
      replacement_place_id: placeId,
      version: draft.version,
    }),
  })
  return readJson<RouteDraft>(response)
}

export const loadCategories = async (): Promise<CategoryOption[]> => {
  const response = await fetch(buildApiUrl('/categories/'))
  return readJson<CategoryOption[]>(response)
}
