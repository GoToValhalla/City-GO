import { buildApiUrl } from '../../shared/api/http'
import type { CategoryOption, RouteDraft, RouteDraftSearchItem } from './routeDraft.types'

const jsonHeaders = { 'Content-Type': 'application/json' }

const readJson = async <T>(response: Response): Promise<T> => {
  if (!response.ok) throw new Error(`HTTP ${response.status}`)
  return response.json() as Promise<T>
}

export const createRandomDraft = async (payload: {
  city_slug: string
  budget_minutes: number
  selected_category_slugs: string[]
  category_mode: 'none' | 'balanced'
  seed?: number
}): Promise<RouteDraft> => {
  const response = await fetch(buildApiUrl('/routes/random'), {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ ...payload, start: { type: 'city_center', label: 'Центр города' } }),
  })
  return readJson<RouteDraft>(response)
}

export const removeDraftPoint = async (draft: RouteDraft, pointId: number): Promise<RouteDraft> => {
  const response = await fetch(buildApiUrl(`/routes/drafts/${draft.draft_id}/remove-point`), {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ point_id: pointId, version: draft.version }),
  })
  return readJson<RouteDraft>(response)
}

export const searchDraftPlaces = async (draft: RouteDraft, q: string): Promise<RouteDraftSearchItem[]> => {
  const query = new URLSearchParams({ q, limit: '8' })
  const response = await fetch(buildApiUrl(`/routes/drafts/${draft.draft_id}/search-places?${query}`))
  return readJson<{ items: RouteDraftSearchItem[] }>(response).then((payload) => payload.items)
}

export const addDraftPoint = async (draft: RouteDraft, placeId: number): Promise<RouteDraft> => {
  const response = await fetch(buildApiUrl(`/routes/drafts/${draft.draft_id}/add-point`), {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ place_id: placeId, after_position: draft.points.at(-1)?.position ?? null, version: draft.version }),
  })
  return readJson<RouteDraft>(response)
}

export const replaceDraftPoint = async (draft: RouteDraft, pointId: number, placeId: number): Promise<RouteDraft> => {
  const response = await fetch(buildApiUrl(`/routes/drafts/${draft.draft_id}/replace-point`), {
    method: 'POST',
    headers: jsonHeaders,
    body: JSON.stringify({ point_id: pointId, replacement_place_id: placeId, version: draft.version }),
  })
  return readJson<RouteDraft>(response)
}

export const loadCategories = async (): Promise<CategoryOption[]> => {
  const response = await fetch(buildApiUrl('/categories/'))
  return readJson<CategoryOption[]>(response)
}
