export type PlaceImageMatchStatus =
  | 'exact_place_photo'
  | 'area_photo'
  | 'category_photo'
  | 'no_photo'

export type PlaceImage = {
  url: string | null
  thumbnail_url: string | null
  source: string
  source_url: string | null
  license: string | null
  attribution: string | null
  match_status: PlaceImageMatchStatus
  match_confidence: 'high' | 'medium' | 'low'
  depicts_qid: string | null
  last_fetched_at: string | null
}

export type Place = {
  id: number
  slug: string
  title: string
  short_description: string | null
  category: string
  address: string
  image_url?: string
  image_id?: number | null
  image_source_type?: string | null
  image_attribution?: string | null
  image_license?: string | null
  image_confidence?: number | null
  image_status?: string | null
  image_reviewed_at?: string | null
  opening_hours?: Record<string, unknown> | null
  average_visit_duration_minutes?: number | null
  open_time?: string
  close_time?: string
  visit_minutes?: number
  price_level?: number | null
  dog_friendly?: boolean
  family_friendly?: boolean
  indoor?: boolean
  outdoor?: boolean
  source?: string
  confidence?: string | number
  existence_confidence_score?: number
  existence_confidence_level?: string
  verification_status?: string
  verification_source?: string | null
  verification_method?: string | null
  verified_at?: string | null
  verified_by?: string | null
  needs_recheck_at?: string | null
  verification_comment?: string | null
  image_source?: string
  image_is_exact?: boolean
  image?: PlaceImage
  tags?: Array<string | { id?: number; code: string; name?: string }>
}

export type PlaceDetail = Place & {
  lat?: number
  lng?: number
  is_active?: boolean
}
