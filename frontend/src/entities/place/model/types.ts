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
  name?: string | null
  short_description: string | null
  description?: string | null
  category: string
  address: string | null
  lat?: number | null
  lng?: number | null
  image_url?: string | null
  photo_url?: string | null
  image_urls?: Array<string | null> | null
  photo_urls?: Array<string | null> | null
  image_id?: number | null
  image_source_type?: string | null
  image_attribution?: string | null
  image_license?: string | null
  image_confidence?: number | null
  image_status?: string | null
  image_reviewed_at?: string | null
  opening_hours?: Record<string, unknown> | string | null
  working_hours?: Record<string, unknown> | string | null
  average_visit_duration_minutes?: number | null
  open_time?: string | null
  close_time?: string | null
  visit_minutes?: number
  price_level?: number | null
  dog_friendly?: boolean
  family_friendly?: boolean
  indoor?: boolean
  outdoor?: boolean
  atmosphere?: string | string[] | null
  inside?: string | string[] | null
  best_for?: string | string[] | null
  phone?: string | null
  website?: string | null
  rating?: number | null
  average_rating?: number | null
  review_count?: number | null
  reviews_count?: number | null
  distance_km?: number | null
  distance_meters?: number | null
  source?: string
  confidence?: string | number
  existence_confidence_score?: number
  existence_confidence_level?: string | null
  verification_status?: string | null
  status?: string | null
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
  lat?: number | null
  lng?: number | null
  is_active?: boolean
}