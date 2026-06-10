import { requireAdminApiToken } from '../../pages/admin/adminToken'
import { buildApiUrl } from '../../shared/api/http'

const adminHeaders = () => ({
  'Content-Type': 'application/json',
  Authorization: `Bearer ${requireAdminApiToken()}`,
})

export type PendingPlaceImage = {
  image_id: number
  place_id: number
  place_title: string
  place_slug: string
  city_slug: string | null
  place_address: string | null
  place_category: string | null
  place_lat: number
  place_lng: number
  image_url: string
  thumbnail_url: string | null
  source_type: string
  source_url: string | null
  attribution: string | null
  license: string | null
  confidence: number | null
  status: string
  created_at: string
}

export type PendingPlaceImagesResponse = {
  items: PendingPlaceImage[]
  total: number
  limit: number
  offset: number
}

const adminBase = () => '/admin/place-images'

export const fetchPendingPlaceImages = async (
  citySlug?: string,
  limit = 50,
  offset = 0,
): Promise<PendingPlaceImagesResponse> => {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  })
  if (citySlug) {
    params.set('city_slug', citySlug)
  }

  const response = await fetch(buildApiUrl(`${adminBase()}/pending?${params.toString()}`), { headers: adminHeaders() })
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }
  return response.json()
}

const postAction = async (imageId: number, action: 'approve' | 'reject' | 'set-primary') => {
  const suffix = action === 'set-primary' ? 'set-primary' : action
  const response = await fetch(buildApiUrl(`${adminBase()}/${imageId}/${suffix}`), {
    method: 'POST',
    headers: adminHeaders(),
    body: action === 'set-primary' ? undefined : JSON.stringify({ reviewer: 'admin-ui' }),
  })
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`)
  }
  return response.json()
}

export const approvePlaceImage = (imageId: number) => postAction(imageId, 'approve')
export const rejectPlaceImage = (imageId: number) => postAction(imageId, 'reject')
export const setPrimaryPlaceImage = (imageId: number) => postAction(imageId, 'set-primary')
